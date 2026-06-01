# Skyrider // RAG Console

A fully local, offline RAG chatbot for querying lecture materials. No API keys, no internet at inference time — everything runs on CPU.

## What it does

Drop PDFs or videos into `data/`, index them, then ask questions in a chat UI. Answers stream with citations (PDF page numbers or video timestamps).

**Stack:** ChromaDB · sentence-transformers (`all-MiniLM-L6-v2`) · faster-whisper · Qwen2.5-1.5B-Instruct (GGUF via llama-cpp) · Streamlit

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

## Run

```bash
uv sync
uv run streamlit run src/app.py
```

Open http://localhost:8501. On first query, the Qwen GGUF model (~1 GB) downloads into `models/` automatically.

## Ingest data

Add PDFs or video/audio files (`.pdf`, `.mp4`, `.mp3`, `.wav`, `.m4a`) to `data/`, then either:

- Click **INDEX PENDING DATA** in the sidebar, or
- Run from the CLI:

```bash
uv run python src/ingest.py
uv run python src/ingest.py --force          # wipe and re-index everything
uv run python src/ingest.py --type pdf       # PDFs only
uv run python src/ingest.py --whisper-model small.en  # more accurate transcription
```

Ingestion is incremental — already-indexed files are skipped unless `--force` is used.

## Query from CLI

```bash
uv run python src/query.py "What is productized enterprise RAG?"
```

## Project layout

```
rag-chatbot/
├── src/
│   ├── app.py          # Streamlit web UI (chat interface + sidebar controls)
│   ├── ingest.py       # Ingestion pipeline: PDF extraction, audio transcription, embedding, ChromaDB insert
│   └── query.py        # Retrieval + LLM answer generation (streaming)
│
├── data/               # [you populate] source PDFs and video/audio files — see "Ingest data" above
├── db/                 # [auto-created] ChromaDB vector store + indexed_files.json manifest
├── models/             # [auto-created] Qwen GGUF weights downloaded from HuggingFace on first query
├── scratch/
│   └── audio_cache/    # [auto-created] MP3s extracted from videos, cached to skip re-transcoding
│
├── .streamlit/
│   └── config.toml     # Forces dark theme so the synthwave UI renders correctly
├── pyproject.toml      # Dependencies (managed by uv)
└── uv.lock             # Locked dependency graph
```

All four runtime directories (`data/`, `db/`, `models/`, `scratch/`) are excluded from git.

- **`data/`** — you must create this and add your files before ingestion will do anything.
- **`db/`** — created automatically on first `uv run python src/ingest.py` run.
- **`models/`** — created automatically on first query; requires a one-time internet connection to download the ~1 GB Qwen model.
- **`scratch/audio_cache/`** — created automatically during video ingestion; safe to delete to free disk space (videos will be re-transcoded on the next ingest).

## Whisper model sizes

| Model | Speed | Accuracy |
|-------|-------|----------|
| `tiny.en` | fastest | lower |
| `base.en` | fast | moderate |
| `small.en` | slower | higher |

Default in the UI is `tiny.en`. Switch in the sidebar before indexing.
