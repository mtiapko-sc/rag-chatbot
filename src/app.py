import time
import streamlit as st

# Set page config at the very beginning
st.set_page_config(
    page_title="SKYRIDER // RAG CONSOLE",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Retro Skyrider Synthwave styling
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
    
    /* Global Background and Scanline CRT effect */
    .stApp {
        background-color: #0d051d !important;
        background-image: 
            linear-gradient(to right, rgba(0, 240, 255, 0.05) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0, 240, 255, 0.05) 1px, transparent 1px) !important;
        background-size: 40px 40px !important;
        color: #e2e8f0 !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    
    /* Scanlines Overlay */
    .stApp::before {
        content: " ";
        display: block;
        position: fixed;
        top: 0; left: 0; bottom: 0; right: 0;
        background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
        z-index: 999999;
        background-size: 100% 4px, 6px 100%;
        pointer-events: none;
        opacity: 0.85;
    }
    
    /* Headers with Retro-Futuristic Glow */
    .app-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 2.8rem;
        font-weight: 900;
        color: #00f0ff;
        text-shadow: 0 0 5px #00f0ff, 0 0 15px #00f0ff, 0 0 30px #ff007f;
        letter-spacing: 4px;
        text-align: center;
        margin-top: 1rem;
        margin-bottom: 0.2rem;
        text-transform: uppercase;
    }
    
    .app-subtitle {
        font-family: 'Share Tech Mono', monospace;
        font-size: 1.1rem;
        color: #ff007f;
        text-shadow: 0 0 5px #ff007f, 0 0 10px rgba(255, 0, 127, 0.5);
        text-align: center;
        margin-bottom: 2.5rem;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    /* Sidebar styling: Retro Terminal */
    [data-testid="stSidebar"] {
        background-color: #06020e !important;
        border-right: 2px solid #ff007f !important;
        box-shadow: 5px 0 20px rgba(255, 0, 127, 0.4) !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    
    /* Sidebar Headers */
    .sidebar-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.5rem;
        font-weight: 700;
        color: #00f0ff;
        text-shadow: 0 0 5px #00f0ff;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 1.5rem;
    }
    
    /* Retro Sidebar Card */
    .sidebar-card {
        background-color: rgba(18, 9, 36, 0.8);
        border: 1px solid #ff007f;
        box-shadow: 0 0 8px rgba(255, 0, 127, 0.3);
        border-radius: 4px;
        padding: 12px;
        margin-bottom: 12px;
    }
    
    .sidebar-card strong {
        color: #00f0ff;
        text-shadow: 0 0 2px #00f0ff;
    }
    
    /* Retro Badges */
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 2px;
        font-size: 0.75rem;
        font-weight: 900;
        text-transform: uppercase;
        margin-top: 5px;
    }
    
    .status-indexed {
        background-color: rgba(0, 240, 255, 0.2);
        color: #00f0ff;
        border: 1px solid #00f0ff;
        box-shadow: 0 0 5px rgba(0, 240, 255, 0.5);
    }
    
    .status-pending {
        background-color: rgba(255, 0, 127, 0.2);
        color: #ff007f;
        border: 1px solid #ff007f;
        box-shadow: 0 0 5px rgba(255, 0, 127, 0.5);
    }
    
    /* Retro Buttons styling */
    div.stButton > button {
        background-color: #ff007f !important;
        color: #ffffff !important;
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 700 !important;
        border: 1px solid #00f0ff !important;
        box-shadow: 0 0 8px #ff007f, inset 0 0 4px #00f0ff !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-radius: 4px !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important;
    }
    
    div.stButton > button:hover {
        background-color: #00f0ff !important;
        color: #06020e !important;
        box-shadow: 0 0 15px #00f0ff, inset 0 0 4px #ff007f !important;
        border: 1px solid #ff007f !important;
    }
    
    /* Streamlit expander retro style */
    div.stExpander {
        background-color: rgba(18, 9, 36, 0.7) !important;
        border: 1px solid #ff007f !important;
        box-shadow: 0 0 10px rgba(255, 0, 127, 0.2) !important;
        border-radius: 4px !important;
        margin-top: 10px !important;
    }
    
    /* Source list styling inside expander */
    .source-card {
        background-color: #06020e;
        border-left: 4px solid #00f0ff;
        border-right: 1px solid #ff007f;
        border-top: 1px solid #ff007f;
        border-bottom: 1px solid #ff007f;
        box-shadow: 0 0 8px rgba(0, 240, 255, 0.1);
        padding: 10px 15px;
        margin-bottom: 10px;
        border-radius: 2px;
    }
    
    .source-title {
        font-family: 'Orbitron', sans-serif;
        font-weight: 700;
        color: #ff007f;
        text-shadow: 0 0 3px #ff007f;
        margin-bottom: 5px;
        font-size: 0.8rem;
    }
    
    .source-text {
        color: #e2e8f0;
        font-style: italic;
    }
    
    /* Chat message area customization */
    [data-testid="stChatMessage"] {
        background-color: rgba(22, 10, 48, 0.75) !important;
        border: 1px solid #ff007f !important;
        box-shadow: 0 0 12px rgba(255, 0, 127, 0.25) !important;
        border-radius: 4px !important;
        margin-bottom: 15px !important;
        padding: 15px !important;
    }
    
    /* Make assistant bubble cyan, user bubble pink */
    [data-testid="stChatMessage"]:nth-child(even) {
        border: 1px solid #00f0ff !important;
        box-shadow: 0 0 12px rgba(0, 240, 255, 0.25) !important;
    }
    
    /* Chat Input Bar customization */
    [data-testid="stChatInput"] {
        background-color: #06020e !important;
        border: 1px solid #00f0ff !important;
        box-shadow: 0 0 10px rgba(0, 240, 255, 0.3) !important;
        border-radius: 4px !important;
        color: #ffffff !important;
    }
    
    textarea[data-testid="stChatInputTextArea"] {
        color: #ffffff !important;
        font-family: 'Share Tech Mono', monospace !important;
    }

    /* Hide Deploy button */
    [data-testid="stAppDeployButton"] {
        display: none !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Imports from src
from ingest import DATA_DIR, load_manifest, run_ingestion
from query import answer_question_stream


def get_all_data_files():
    """Scan the data directory and return status of files."""
    supported_extensions = {".pdf", ".mp4", ".mp3", ".wav", ".m4a"}
    if not DATA_DIR.exists():
        return []

    manifest = load_manifest()
    files_status = []

    for item in DATA_DIR.iterdir():
        if item.is_file() and item.suffix.lower() in supported_extensions:
            is_indexed = item.name in manifest
            files_status.append(
                {
                    "name": item.name,
                    "size_mb": item.stat().st_size / (1024 * 1024),
                    "is_indexed": is_indexed,
                    "type": "PDF Slide"
                    if item.suffix.lower() == ".pdf"
                    else "Video/Audio",
                }
            )

    # Sort: indexed first, then by name
    files_status.sort(key=lambda x: (not x["is_indexed"], x["name"]))
    return files_status


# --- SIDEBAR: KNOWLEDGE BASE CONTROLLER ---
with st.sidebar:
    st.markdown(
        "<div class='sidebar-title'>Skyrider Console</div>", unsafe_allow_html=True
    )
    st.markdown("SYSTEM STATUS // INTERNET DISCONNECTED // CPU ONLY")

    st.markdown("### MODEL CONFIG")
    whisper_model = st.selectbox(
        "Whisper Speech-to-Text Model",
        options=["tiny.en", "base.en", "small.en"],
        index=0,  # Default to tiny.en for fast CPU processing
        help="tiny is faster but less accurate. base/small are more accurate but slower on CPU.",
    )

    st.markdown("---")
    st.markdown("### INDEX MANIFEST")

    # List files
    files = get_all_data_files()
    if not files:
        st.warning("No files found in `./data/`. Please add PDFs or MP4 videos.")
    else:
        for f in files:
            badge_class = "status-indexed" if f["is_indexed"] else "status-pending"
            badge_text = "INDEXED" if f["is_indexed"] else "PENDING"

            st.markdown(
                f"<div class='sidebar-card'>"
                f"<strong>{f['name']}</strong><br>"
                f"<span style='font-size: 0.8rem; color: #94a3b8;'>{f['type']} • {f['size_mb']:.1f} MB</span><br>"
                f"<span class='status-badge {badge_class}'>{badge_text}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # Rebuild Index button
    st.markdown("### CONTROL CHANNELS")
    if st.button("INDEX PENDING DATA", use_container_width=True):
        with st.spinner("TRANSCRIBING/INDEXING SYSTEM ACTIVE..."):
            log_container = st.empty()
            log_container.info("Loading models and checking data folder...")

            try:
                start_time = time.time()
                run_ingestion(whisper_model=whisper_model, force_reindex=False)
                log_container.success(
                    f"INGESTION COMPLETE: {time.time() - start_time:.1f}s"
                )
                time.sleep(2)
                st.rerun()
            except Exception as e:
                log_container.error(f"SYSTEM FAULT during ingestion: {e}")

    if st.button(
        "RESET VECTOR STORE (WIPE)",
        use_container_width=True,
        help="Deletes the database and starts indexing from scratch",
    ):
        with st.spinner("WIPING LOCAL DATABASE..."):
            try:
                run_ingestion(whisper_model=whisper_model, force_reindex=True)
                st.success("DATABASE PURGED AND REINDEXED!")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.error(f"SYSTEM FAULT during rebuild: {e}")


# --- MAIN PANEL: CHAT INTERFACE ---
st.markdown(
    "<div class='app-title'>🚀 Skyrider // RAG-Console</div>", unsafe_allow_html=True
)
st.markdown(
    "<div class='app-subtitle'>Local Retrieval-Augmented Generation terminal</div>",
    unsafe_allow_html=True,
)


# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    # Set chat bubbles: User gets Orbitron style header, content in Share Tech Mono
    role_color = "#ff007f" if message["role"] == "user" else "#00f0ff"
    role_name = "USER" if message["role"] == "user" else "SKYRIDER"

    with st.chat_message(message["role"]):
        st.markdown(
            f"<div style='font-family: Orbitron; font-weight:700; color:{role_color}; margin-bottom:5px;'>// {role_name}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(message["content"])

        # If there are sources for this message, show them
        if (
            message["role"] == "assistant"
            and "sources" in message
            and message["sources"]
        ):
            with st.expander("🔍 RETRIEVED DATABANKS"):
                for idx, src in enumerate(message["sources"]):
                    st.markdown(
                        f"<div class='source-card'>"
                        f"<div class='source-title'>[{idx + 1}] {src['citation']} (distance: {src['distance']:.3f})</div>"
                        f"<div class='source-text'>\"{src['text']}\"</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

# React to user input
if prompt := st.chat_input("Input query command..."):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(
            "<div style='font-family: Orbitron; font-weight:700; color:#ff007f; margin-bottom:5px;'>// USER</div>",
            unsafe_allow_html=True,
        )
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        st.markdown(
            "<div style='font-family: Orbitron; font-weight:700; color:#00f0ff; margin-bottom:5px;'>// SKYRIDER</div>",
            unsafe_allow_html=True,
        )
        message_placeholder = st.empty()
        sources_placeholder = st.empty()

        full_response = ""
        sources = []

        message_placeholder.markdown("*SEARCHING RETRIEVAL GRID...*")

        # Get streaming response
        response_generator = answer_question_stream(prompt)

        for chunk in response_generator:
            if chunk["type"] == "sources":
                sources = chunk["data"]
            elif chunk["type"] == "content":
                full_response += chunk["data"]
                # Update UI in real-time with standard terminal block cursor █
                message_placeholder.markdown(full_response + "█")
            elif chunk["type"] == "error":
                message_placeholder.error(f"SYSTEM FAULT: {chunk['data']}")

        # Final update without cursor
        message_placeholder.markdown(
            full_response if full_response else "No matches returned in databanks."
        )

        # Render citations
        if sources:
            with sources_placeholder.expander("🔍 RETRIEVED DATABANKS"):
                for idx, src in enumerate(sources):
                    st.markdown(
                        f"<div class='source-card'>"
                        f"<div class='source-title'>[{idx + 1}] {src['citation']} (distance: {src['distance']:.3f})</div>"
                        f"<div class='source-text'>\"{src['text']}\"</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        # Add assistant response to chat history
        st.session_state.messages.append(
            {"role": "assistant", "content": full_response, "sources": sources}
        )
