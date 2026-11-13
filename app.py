import re
import time
import traceback
import queue
import threading
from pathlib import Path

import streamlit as st

from telegram_service import (
    get_telegram_chats,
    get_chat_messages,
    stream_telegram_file_to_drive,
)
from google_drive_service import (
    get_drive_service,
    get_or_create_folder,
    get_root_folder_id,
)

st.set_page_config(page_title="TG Drive Manager", page_icon="☁️", layout="wide")
css_file = Path(__file__).parent / "style.css"
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def format_size(size):
    size = int(size or 0)
    if size >= 1024 ** 3:
        return f"{size / 1024**3:.2f} GB"
    if size >= 1024 ** 2:
        return f"{size / 1024**2:.2f} MB"
    if size >= 1024:
        return f"{size / 1024:.2f} KB"
    return f"{size} Bytes"


def safe_folder_name(name):
    name = re.sub(r'[<>:"/\\\\|?*]', "_", name or "")
    return name.strip(" .") or "Telegram Chat"


for key, value in {
    "chats": [],
    "attachments": [],
    "selected_chat_id": None,
    "selected_chat_name": None,
    "selected_chat_key": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

with st.sidebar:
    st.image("assets/logo.png", width=220)

    st.markdown("---")
    st.markdown("### Workspace")
    st.markdown(
        '<div class="nav-active">▦ &nbsp; Dashboard</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="nav-item">◉ &nbsp; Telegram browser</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="nav-item">☁ &nbsp; Drive transfers</div>',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### Connections")
    st.markdown(
        f'<div class="status-row"><i></i> Telegram '
        f'<span>{"Chats loaded" if st.session_state["chats"] else "Ready"}</span></div>'
        '<div class="status-row"><i></i> Google Drive <span>On demand</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("Local session · Keep credentials private")
    st.markdown("---")
    st.markdown("### Workspace")
    st.markdown('<div class="nav-active">▦ &nbsp; Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-item">◉ &nbsp; Telegram browser</div>', unsafe_allow_html=True)
    st.markdown('<div class="nav-item">☁ &nbsp; Drive transfers</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### Connections")
    st.markdown(
        f'<div class="status-row"><i></i> Telegram <span>{"Chats loaded" if st.session_state["chats"] else "Ready"}</span></div>'
        '<div class="status-row"><i></i> Google Drive <span>On demand</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("Local session · Keep credentials private")

st.markdown(
    """
    <section class="hero">
      <div class="hero-copy">
        <div class="eyebrow"><i></i> DIRECT CLOUD TRANSFER</div>
        <h1>Your files,<br><em>one destination.</em></h1>
        <p>Browse Telegram chats, choose your media, and stream it straight to Google Drive.</p>
        <div class="chips"><span>✦ No full local download</span><span>✦ Chunked transfer</span><span>✦ Organized storage</span></div>
      </div>
      <div class="hero-visual"><div class="orbit orbit-a"></div><div class="orbit orbit-b"></div><div class="cloud">☁</div><div class="upload-arrow">↑</div><b class="spark s1"></b><b class="spark s2"></b><b class="spark s3"></b></div>
    </section>
    """,
    unsafe_allow_html=True,
)

chat_count = len(st.session_state["chats"])
attachment_count = len(st.session_state["attachments"])
total_size = sum(x.get("size", 0) for x in st.session_state["attachments"])
a, b, c = st.columns(3)
for col, icon, label, value, note in [
    (a, "▦", "TELEGRAM CHATS", str(chat_count), "Chats loaded"),
    (b, "▤", "DETECTED FILES", str(attachment_count), "Current scan"),
    (c, "⇧", "SCANNED SIZE", format_size(total_size), "Attachment size"),
]:
    with col:
        st.markdown(
            f'<div class="metric-card"><div class="metric-icon">{icon}</div><small>{label}</small><strong>{value}</strong><span>{note}</span></div>',
            unsafe_allow_html=True,
        )

st.markdown('<div class="section-title"><span>01</span><div><h2>Telegram workspace</h2><p>Connect to Telegram and choose a chat to explore.</p></div></div>', unsafe_allow_html=True)
load_col, note_col = st.columns([1, 2], vertical_alignment="center")
with load_col:
    if st.button("↻  Load Telegram chats", use_container_width=True):
        try:
            with st.spinner("Connecting to Telegram..."):
                st.session_state["chats"] = get_telegram_chats()
            st.session_state["attachments"] = []
            st.success(f"Loaded {len(st.session_state['chats'])} Telegram chats.")
            st.rerun()
        except Exception as error:
            st.error(f"Telegram error: {error}")
with note_col:
    st.markdown('<div class="note">Your Telegram session is accessed locally. Never share your session file or API credentials.</div>', unsafe_allow_html=True)

chats = st.session_state["chats"]
if chats:
    chat_options = {f"{chat['name']} ({chat['type']})": chat for chat in chats}
    selected_name = st.selectbox("Select Telegram chat or channel", list(chat_options.keys()))
    selected_chat = chat_options[selected_name]
    x, y, z = st.columns([2, 1, 1])
    x.markdown(f'<div class="info-tile"><small>SELECTED CHAT</small><b>{selected_chat["name"]}</b></div>', unsafe_allow_html=True)
    y.markdown(f'<div class="info-tile"><small>CHAT TYPE</small><b>{selected_chat["type"]}</b></div>', unsafe_allow_html=True)
    z.markdown(f'<div class="info-tile"><small>UNREAD</small><b>{selected_chat.get("unread", 0)}</b></div>', unsafe_allow_html=True)

    scan_col, scan_button_col = st.columns([1, 1], vertical_alignment="bottom")
    with scan_col:
        message_limit = st.number_input("Recent messages to scan", min_value=10, max_value=500, value=50, step=10)
    with scan_button_col:
        if st.button("⌕  Browse attachments", type="primary", use_container_width=True):
            try:
                with st.spinner("Scanning Telegram messages..."):
                    found = get_chat_messages(selected_chat["id"], int(message_limit))
                st.session_state["attachments"] = found
                st.session_state["selected_chat_id"] = selected_chat["id"]
                st.session_state["selected_chat_name"] = selected_chat["name"]
                st.session_state["selected_chat_key"] = selected_name
                st.success(f"Found {len(found)} attachments.")
                st.rerun()
            except Exception as error:
                st.error(f"Attachment scanning failed: {error}")
else:
    st.markdown('<div class="empty"><div>✦</div><h3>Your Telegram workspace is waiting</h3><p>Load your Telegram chats to begin browsing media.</p></div>', unsafe_allow_html=True)

attachments = st.session_state["attachments"]
if attachments:
    st.markdown('<div class="section-title"><span>02</span><div><h2>Media library</h2><p>Filter attachments and select what you want to transfer.</p></div></div>', unsafe_allow_html=True)
    videos = sum(1 for item in attachments if item.get("type") == "Video")
    photos = sum(1 for item in attachments if item.get("type") == "Photo")
    docs = sum(1 for item in attachments if item.get("type") == "Document")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("All files", len(attachments))
    m2.metric("Videos", videos)
    m3.metric("Photos", photos)
    m4.metric("Documents", docs)

    filter_type = st.selectbox("Filter attachment type", ["All", "Video", "Photo", "Document"])
    filtered = attachments if filter_type == "All" else [i for i in attachments if i.get("type") == filter_type]
    label_to_item = {}
    for index, item in enumerate(filtered):
        label = f"{item['filename']} | {format_size(item['size'])} | Message {item['message_id']} | #{index + 1}"
        label_to_item[label] = item
    options = list(label_to_item)
    select_all = st.checkbox("Select all displayed attachments", key=f"select_all_{filter_type}")
    selected_labels = st.multiselect("Choose files to upload", options, default=options if select_all else [], key=f"selected_files_{filter_type}")
    selected_items = [label_to_item[label] for label in selected_labels]
    selected_size = sum(item.get("size", 0) for item in selected_items)
    st.markdown(
        f'<div class="selection"><div><strong>{len(selected_items)}</strong> files selected <span>· {format_size(selected_size)}</span></div><small>READY TO TRANSFER</small></div>',
        unsafe_allow_html=True,
    )
    with st.expander("Preview selected files"):
        if selected_items:
            for item in selected_items:
                st.write(f"📄 {item['filename']} — {format_size(item['size'])}")
        else:
            st.caption("No files selected.")

    st.markdown('<div class="section-title"><span>03</span><div><h2>Google Drive transfer</h2><p>Stream selected Telegram media into your Drive destination.</p></div></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="destination"><div class="destination-icon">☁</div><div><small>DESTINATION FOLDER</small><b>BB M D3</b><p>Files grouped by chat and media type.</p></div><span>● Ready</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("Direct streaming is enabled. The complete media file is not intentionally saved to your laptop.")

    if st.button("⇧  Start upload", type="primary", use_container_width=True, disabled=not selected_items):
        successful, failed = 0, 0
        overall_progress = st.progress(0)
        overall_status = st.empty()
        try:
            with st.spinner("Connecting to Google Drive..."):
                drive_service = get_drive_service()
                root_folder_id = get_root_folder_id()
            chat_folder_id = get_or_create_folder(
                drive_service,
                safe_folder_name(st.session_state["selected_chat_name"]),
                root_folder_id,
            )

            for index, item in enumerate(selected_items):
                filename = item["filename"]
                st.markdown(
                    f'<div class="file-row"><span>⇧</span><div><b>{filename}</b><small>{format_size(item["size"])}</small></div><small>{index + 1}/{len(selected_items)}</small></div>',
                    unsafe_allow_html=True,
                )
                try:
                    type_folder_id = get_or_create_folder(drive_service, item["type"] + "s", chat_folder_id)
                    file_progress = st.progress(0)
                    progress_text = st.empty()
                    speed_text = st.empty()
                    progress_queue = queue.Queue()
                    transfer_result, transfer_errors = {}, {}

                    def transfer_worker(current_item=item, current_filename=filename, current_folder_id=type_folder_id):
                        try:
                            transfer_result["result"] = stream_telegram_file_to_drive(
                                chat_id=current_item["chat_id"],
                                message_id=current_item["message_id"],
                                filename=current_filename,
                                mime_type=current_item["mime_type"],
                                file_size=current_item["size"],
                                drive_folder_id=current_folder_id,
                                progress_callback=lambda current, total: progress_queue.put((current, total)),
                            )
                        except Exception as transfer_error:
                            transfer_errors["error"] = transfer_error
                            transfer_errors["traceback"] = traceback.format_exc()

                    previous_bytes, previous_time = 0, time.monotonic()
                    transfer_thread = threading.Thread(target=transfer_worker, name="TelegramDriveTransfer", daemon=True)
                    transfer_thread.start()
                    while transfer_thread.is_alive() or not progress_queue.empty():
                        try:
                            current, total = progress_queue.get(timeout=0.2)
                        except queue.Empty:
                            continue
                        if total and total > 0:
                            percent = min(max(current / total, 0.0), 1.0)
                            file_progress.progress(percent)
                            now = time.monotonic()
                            elapsed = now - previous_time
                            if elapsed > 0:
                                speed = max(0, current - previous_bytes) / elapsed
                                speed_text.caption(f"Transfer rate: {format_size(int(speed))}/s")
                            previous_bytes, previous_time = current, now
                            progress_text.caption(f"{format_size(current)} / {format_size(total)} ({percent * 100:.1f}%)")
                    transfer_thread.join()

                    if "error" in transfer_errors:
                        raise RuntimeError(f"{transfer_errors['error']}\n\n{transfer_errors['traceback']}") from transfer_errors["error"]
                    result = transfer_result.get("result")
                    if result is None:
                        raise RuntimeError("Transfer ended without returning a Google Drive result.")
                    file_progress.progress(1.0)
                    progress_text.caption(f"{format_size(item['size'])} / {format_size(item['size'])} (100%)")
                    successful += 1
                    st.success(f"Successfully uploaded: {filename}")
                    if result.get("webViewLink"):
                        st.markdown(f"[Open in Google Drive]({result['webViewLink']})")
                except Exception as error:
                    failed += 1
                    st.error(f"Upload failed: {filename}")
                    st.code(repr(error))
                    if isinstance(error, RuntimeError) and "\n" in str(error):
                        st.code(str(error), language="text")
                    else:
                        st.code(traceback.format_exc(), language="text")
                    traceback.print_exc()

                overall_progress.progress((index + 1) / len(selected_items))
                overall_status.caption(f"Completed {index + 1} of {len(selected_items)} files")

            st.markdown('<div class="section-title"><span>✓</span><div><h2>Transfer summary</h2><p>Your upload batch has finished.</p></div></div>', unsafe_allow_html=True)
            r1, r2, r3 = st.columns(3)
            r1.metric("Selected", len(selected_items))
            r2.metric("Successful", successful)
            r3.metric("Failed", failed)
            if failed == 0:
                st.success("All selected files uploaded successfully!")
            else:
                st.warning("Some files failed. Check the error details above.")
        except Exception as error:
            st.error("Google Drive setup/upload process failed.")
            st.code(repr(error))
            st.code(traceback.format_exc(), language="text")
            traceback.print_exc()
elif chats:
    st.markdown('<div class="empty compact"><div>▤</div><h3>No media scanned yet</h3><p>Select a chat and browse its attachments to get started.</p></div>', unsafe_allow_html=True)

st.markdown('<footer class="footer"><b>TG DRIVE MANAGER</b><span>Telegram → Google Drive · Concurrent streaming edition</span></footer>', unsafe_allow_html=True)
