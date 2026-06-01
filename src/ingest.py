import json
import time
import subprocess
from pathlib import Path
import fitz  # PyMuPDF
import imageio_ffmpeg
from faster_whisper import WhisperModel
from sentence_transformers import SentenceTransformer
import chromadb

# Directories
WORKSPACE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = WORKSPACE_DIR / "data"
DB_DIR = WORKSPACE_DIR / "db"
MANIFEST_PATH = DB_DIR / "indexed_files.json"
TEMP_AUDIO_DIR = WORKSPACE_DIR / "scratch" / "audio_cache"

# Ensure directories exist
DB_DIR.mkdir(exist_ok=True)
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


def load_manifest():
    """Load the manifest of already indexed files."""
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_manifest(manifest):
    """Save the manifest of indexed files."""
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)


def get_file_metadata(file_path: Path):
    """Get file size and modification time to check for changes."""
    stats = file_path.stat()
    return {"size": stats.st_size, "mtime": stats.st_mtime, "indexed_at": time.time()}


def extract_pdf_pages(pdf_path: Path):
    """Extract text page-by-page from a PDF."""
    print(f"Extracting text from PDF: {pdf_path.name}")
    pages = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        text = page.get_text().strip()
        if text:
            pages.append(
                {
                    "text": text,
                    "metadata": {
                        "source": pdf_path.name,
                        "type": "pdf",
                        "page": i + 1,
                        "total_pages": len(doc),
                    },
                }
            )
    doc.close()
    return pages


def extract_audio_from_video(video_path: Path, output_audio_path: Path):
    """Extract audio from video file using imageio-ffmpeg static binary."""
    print(f"Extracting audio from video: {video_path.name}")
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()

    # We convert to mono, 16kHz MP3 to keep the cache size small and optimal for Whisper
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_audio_path),
    ]

    # Run ffmpeg with output redirection
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg audio extraction failed: {result.stderr.decode('utf-8')}"
        )


def transcribe_audio(audio_path: Path, whisper_model_name="base.en"):
    """Transcribe audio file using faster-whisper on CPU."""
    print(f"Transcribing audio with faster-whisper ({whisper_model_name})...")
    # Initialize WhisperModel
    # device="cpu", compute_type="int8" is the fastest/safest CPU setup
    model = WhisperModel(whisper_model_name, device="cpu", compute_type="int8")

    segments, info = model.transcribe(str(audio_path), beam_size=5)

    transcript_segments = []
    for segment in segments:
        transcript_segments.append(
            {"start": segment.start, "end": segment.end, "text": segment.text.strip()}
        )
    return transcript_segments


def chunk_transcription(segments, source_name, window_size_words=150, overlap_words=30):
    """
    Group transcription segments into larger semantic chunks using a sliding window.
    Ensures that context isn't lost across thin segment boundaries.
    """
    chunks = []
    current_words = []
    current_start = 0.0

    for i, seg in enumerate(segments):
        words = seg["text"].split()
        if not words:
            continue

        if not current_words:
            current_start = seg["start"]

        current_words.extend(words)

        # When we exceed window_size_words, create a chunk
        if len(current_words) >= window_size_words:
            chunk_text = " ".join(current_words)
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": {
                        "source": source_name,
                        "type": "video",
                        "start_time": current_start,
                        "end_time": seg["end"],
                    },
                }
            )

            # Keep overlap words
            # Find how many segments to slide back to retain roughly overlap_words
            overlap_words_collected = []
            slide_back_idx = i
            while slide_back_idx >= 0 and len(overlap_words_collected) < overlap_words:
                overlap_words_collected = (
                    segments[slide_back_idx]["text"].split() + overlap_words_collected
                )
                slide_back_idx -= 1

            current_words = overlap_words_collected
            if slide_back_idx + 1 < len(segments):
                current_start = segments[slide_back_idx + 1]["start"]
            else:
                current_start = seg["start"]

    # Add any remaining words at the end
    if current_words:
        chunk_text = " ".join(current_words)
        chunks.append(
            {
                "text": chunk_text,
                "metadata": {
                    "source": source_name,
                    "type": "video",
                    "start_time": current_start,
                    "end_time": segments[-1]["end"] if segments else 0.0,
                },
            }
        )

    return chunks


def process_file(
    file_path: Path,
    embed_model: SentenceTransformer,
    collection,
    whisper_model_name="base.en",
):
    """Process a single file: extract text, chunk, embed, and insert into ChromaDB."""
    file_ext = file_path.suffix.lower()
    chunks = []

    if file_ext == ".pdf":
        pages = extract_pdf_pages(file_path)
        # For PDF slides, we chunk by page. If a page has text, it becomes a chunk.
        for page in pages:
            # Clean text and skip empty slides
            text = page["text"]
            # If text is very long, we could optionally split it, but slides are usually short.
            chunks.append({"text": text, "metadata": page["metadata"]})

    elif file_ext in [".mp4", ".mp3", ".wav", ".m4a"]:
        audio_path = TEMP_AUDIO_DIR / f"{file_path.stem}.mp3"

        # 1. Extract audio if file is video
        if file_ext == ".mp4":
            if not audio_path.exists():
                extract_audio_from_video(file_path, audio_path)
            else:
                print(f"Using cached audio for video: {file_path.name}")
        else:
            # Just copy or link for direct audio formats
            audio_path = file_path

        # 2. Transcribe audio
        segments = transcribe_audio(audio_path, whisper_model_name)

        # 3. Chunk transcription
        chunks = chunk_transcription(segments, file_path.name)

        # Clean up temporary audio files if we created them and don't want to cache
        # (We keep them in TEMP_AUDIO_DIR to speed up development re-runs)

    else:
        print(f"Skipping unsupported file format: {file_path.name}")
        return False

    if not chunks:
        print(f"No text extracted/chunked from {file_path.name}")
        return False

    print(
        f"Generated {len(chunks)} chunks for {file_path.name}. Generating embeddings and saving to DB..."
    )

    # Batch embed and insert
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [f"{file_path.name}_chunk_{i}" for i in range(len(chunks))]

    embeddings = embed_model.encode(texts, show_progress_bar=True)

    # Store in ChromaDB
    collection.add(
        ids=ids, embeddings=embeddings.tolist(), documents=texts, metadatas=metadatas
    )

    return True


def run_ingestion(whisper_model="base.en", force_reindex=False, file_type="all"):
    """Main function to scan data directory and index new files."""
    manifest = load_manifest()

    # 1. Initialize models
    print("Loading embedding model (all-MiniLM-L6-v2)...")
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    # 2. Initialize ChromaDB
    chroma_client = chromadb.PersistentClient(path=str(DB_DIR))
    # We clear collection if force_reindex is specified
    if force_reindex:
        try:
            chroma_client.delete_collection("rag_knowledge_base")
            print("Deleted existing vector collection for force re-indexing.")
        except Exception:
            pass

    collection = chroma_client.get_or_create_collection(name="rag_knowledge_base")

    # 3. Scan files
    files_to_process = []
    if not DATA_DIR.exists():
        print(f"Data directory {DATA_DIR} does not exist!")
        return

    if file_type == "pdf":
        supported_extensions = {".pdf"}
    elif file_type == "video":
        supported_extensions = {".mp4", ".mp3", ".wav", ".m4a"}
    else:
        supported_extensions = {".pdf", ".mp4", ".mp3", ".wav", ".m4a"}

    for item in DATA_DIR.iterdir():
        if item.is_file() and item.suffix.lower() in supported_extensions:
            file_meta = get_file_metadata(item)

            # Check if file has changed or is new
            old_meta = manifest.get(item.name)
            if (
                force_reindex
                or not old_meta
                or old_meta["size"] != file_meta["size"]
                or old_meta["mtime"] != file_meta["mtime"]
            ):
                files_to_process.append((item, file_meta))
            else:
                print(f"Skipping already indexed file: {item.name}")

    if not files_to_process:
        print("No new files to ingest for the specified type.")
        return

    print(f"Found {len(files_to_process)} files to process.")

    for file_path, file_meta in files_to_process:
        try:
            start_time = time.time()
            success = process_file(file_path, embed_model, collection, whisper_model)
            if success:
                manifest[file_path.name] = file_meta
                save_manifest(manifest)
                print(
                    f"Successfully indexed {file_path.name} in {time.time() - start_time:.2f} seconds.\n"
                )
        except Exception as e:
            print(f"Error processing file {file_path.name}: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingest PDFs and videos into local ChromaDB"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-indexing of all files"
    )
    parser.add_argument(
        "--whisper-model",
        default="base.en",
        help="Whisper model size (tiny.en, base.en, etc.)",
    )
    parser.add_argument(
        "--type",
        choices=["all", "pdf", "video"],
        default="all",
        help="File type to ingest",
    )
    args = parser.parse_args()

    run_ingestion(
        whisper_model=args.whisper_model, force_reindex=args.force, file_type=args.type
    )
