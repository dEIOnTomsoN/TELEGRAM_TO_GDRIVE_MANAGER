import re
import time
import traceback
import queue
import threading
import streamlit as st

from telegram_service import (
    get_telegram_chats,
    get_chat_messages,
    stream_telegram_file_to_drive
)

from google_drive_service import (
    get_drive_service,
    get_or_create_folder,
    get_root_folder_id
)


# -----------------------------------
# PAGE CONFIGURATION
# -----------------------------------

st.set_page_config(
    page_title="Telegram Drive Manager",
    page_icon="📁",
    layout="wide"
)

st.title("📁 Telegram Drive Manager")

st.caption(
    "High-performance Telegram to Google Drive transfer"
)


# -----------------------------------
# HELPERS
# -----------------------------------

def format_size(size):

    if size >= 1024 ** 3:
        return f"{size / 1024**3:.2f} GB"

    if size >= 1024 ** 2:
        return f"{size / 1024**2:.2f} MB"

    if size >= 1024:
        return f"{size / 1024:.2f} KB"

    return f"{size} Bytes"


def safe_folder_name(name):

    name = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        name or ""
    )

    return name.strip(" .") or "Telegram Chat"


# -----------------------------------
# SESSION INITIALIZATION
# -----------------------------------

if "chats" not in st.session_state:
    st.session_state["chats"] = []

if "attachments" not in st.session_state:
    st.session_state["attachments"] = []


# -----------------------------------
# TELEGRAM CHATS
# -----------------------------------

st.header("1. Telegram Chats")

if st.button(
    "🔄 Load Telegram Chats",
    use_container_width=True
):

    try:

        with st.spinner("Connecting to Telegram..."):

            chats = get_telegram_chats()

            st.session_state["chats"] = chats
            st.session_state["attachments"] = []

        st.success(
            f"Found {len(chats)} Telegram chats."
        )

    except Exception as error:

        st.error(f"Telegram error: {error}")


# -----------------------------------
# SELECT CHAT
# -----------------------------------

chats = st.session_state["chats"]

if chats:

    chat_options = {
        f"{chat['name']} ({chat['type']})": chat
        for chat in chats
    }

    selected_name = st.selectbox(
        "Select Telegram chat or channel",
        list(chat_options.keys())
    )

    selected_chat = chat_options[selected_name]

    col1, col2 = st.columns(2)

    col1.metric(
        "Selected Chat",
        selected_chat["name"]
    )

    col2.metric(
        "Unread Messages",
        selected_chat["unread"]
    )

    message_limit = st.number_input(
        "Recent messages to scan",
        min_value=10,
        max_value=500,
        value=50,
        step=10
    )

    if st.button(
        "📂 Browse Attachments",
        type="primary",
        use_container_width=True
    ):

        try:

            with st.spinner("Scanning Telegram messages..."):

                attachments = get_chat_messages(
                    selected_chat["id"],
                    int(message_limit)
                )

            st.session_state["attachments"] = attachments

            st.session_state["selected_chat_id"] = (
                selected_chat["id"]
            )

            st.session_state["selected_chat_name"] = (
                selected_chat["name"]
            )

            st.session_state["selected_chat_key"] = (
                selected_name
            )

            st.success(
                f"Found {len(attachments)} attachments."
            )

        except Exception as error:

            st.error(
                f"Attachment scanning failed: {error}"
            )


# -----------------------------------
# ATTACHMENT BROWSER
# -----------------------------------

attachments = st.session_state["attachments"]

if attachments:

    st.divider()

    st.header("2. Select Attachments")

    total_size = sum(
        item["size"] for item in attachments
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Attachments",
        len(attachments)
    )

    col2.metric(
        "Total Size",
        format_size(total_size)
    )

    col3.metric(
        "Videos",
        sum(
            1 for item in attachments
            if item["type"] == "Video"
        )
    )

    filter_type = st.selectbox(
        "Filter attachment type",
        ["All", "Video", "Photo", "Document"]
    )

    if filter_type == "All":

        filtered = attachments

    else:

        filtered = [
            item for item in attachments
            if item["type"] == filter_type
        ]

    label_to_item = {}

    for item in filtered:

        label = (
            f"{item['filename']} | "
            f"{format_size(item['size'])} | "
            f"Message {item['message_id']}"
        )

        label_to_item[label] = item

    options = list(label_to_item.keys())

    select_all = st.checkbox(
        "Select all displayed attachments",
        key="select_all_files"
    )

    selected_labels = st.multiselect(
        "Choose files to upload",
        options=options,
        default=options if select_all else [],
        key="selected_files"
    )

    selected_items = [
        label_to_item[label]
        for label in selected_labels
    ]

    selected_size = sum(
        item["size"] for item in selected_items
    )

    st.info(
        f"Selected: {len(selected_items)} files "
        f"({format_size(selected_size)})"
    )

    with st.expander("Preview selected files"):

        for item in selected_items:

            st.write(
                f"📄 {item['filename']} — "
                f"{format_size(item['size'])}"
            )


    # -----------------------------------
    # GOOGLE DRIVE UPLOAD
    # -----------------------------------

    st.divider()

    st.header("3. Direct Google Drive Upload")

    st.write("Destination: **BB M D3**")

    st.caption(
        "Concurrent streaming enabled. "
        "No complete video is saved to your laptop."
    )

    if st.button(
        "🚀 Start Fast Upload",
        type="primary",
        use_container_width=True,
        disabled=not selected_items
    ):

        successful = 0
        failed = 0

        overall_progress = st.progress(0)
        overall_status = st.empty()

        try:

            with st.spinner("Connecting to Google Drive..."):

                drive_service = get_drive_service()

                root_folder_id = get_root_folder_id()

            chat_folder_id = get_or_create_folder(
                drive_service,
                safe_folder_name(
                    st.session_state["selected_chat_name"]
                ),
                root_folder_id
            )

            for index, item in enumerate(selected_items):

                filename = item["filename"]

                st.divider()

                st.subheader(
                    f"File {index + 1}/{len(selected_items)}"
                )

                st.write(f"**{filename}**")

                st.write(
                    f"File size: {format_size(item['size'])}"
                )

                try:

                    # Create media folder
                    type_folder_id = get_or_create_folder(
                        drive_service,
                        item["type"] + "s",
                        chat_folder_id
                    )

                    file_progress = st.progress(0)

                    progress_text = st.empty()

                    speed_text = st.empty()

                    # Progress callbacks can run inside the uploader thread.
                    # Send progress through a queue and update Streamlit only here.
                    progress_queue = queue.Queue()
                    transfer_result = {}
                    transfer_errors = {}

                    def transfer_worker():
                        try:
                            transfer_result["result"] = stream_telegram_file_to_drive(
                                chat_id=item["chat_id"],
                                message_id=item["message_id"],
                                filename=filename,
                                mime_type=item["mime_type"],
                                file_size=item["size"],
                                drive_folder_id=type_folder_id,
                                progress_callback=lambda current, total: (
                                    progress_queue.put((current, total))
                                )
                            )
                        except Exception as transfer_error:
                            transfer_errors["error"] = transfer_error
                            transfer_errors["traceback"] = traceback.format_exc()

                    previous_bytes = 0
                    previous_time = time.monotonic()

                    transfer_thread = threading.Thread(
                        target=transfer_worker,
                        name="TelegramDriveTransfer",
                        daemon=True
                    )
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
                                speed_text.caption(
                                    f"Current upload rate: "
                                    f"{format_size(int(speed))}/s"
                                )

                            previous_bytes = current
                            previous_time = now

                            progress_text.caption(
                                f"{format_size(current)} / "
                                f"{format_size(total)} "
                                f"({percent * 100:.1f}%)"
                            )

                    transfer_thread.join()

                    if "error" in transfer_errors:
                        raise RuntimeError(
                            f"{transfer_errors['error']}\\n\\n"
                            f"{transfer_errors['traceback']}"
                        ) from transfer_errors["error"]

                    result = transfer_result.get("result")
                    if result is None:
                        raise RuntimeError(
                            "The transfer ended without returning a Google Drive result."
                        )

                    file_progress.progress(1.0)
                    progress_text.caption(
                        f"{format_size(item['size'])} / "
                        f"{format_size(item['size'])} (100.0%)"
                    )

                    successful += 1

                    st.success(
                        f"Successfully uploaded: {filename}"
                    )

                    if result.get("webViewLink"):

                        st.markdown(
                            f"[Open in Google Drive]"
                            f"({result['webViewLink']})"
                        )

                except Exception as error:

                    failed += 1

                    st.error(f"Upload failed: {filename}")
                    st.write("**Exception details:**")
                    st.code(repr(error))
                    st.write("**Full traceback:**")
                    if isinstance(error, RuntimeError) and "\\n" in str(error):
                        st.code(str(error), language="text")
                    else:
                        st.code(traceback.format_exc(), language="text")
                    traceback.print_exc()

                overall_progress.progress(
                    (index + 1) / len(selected_items)
                )

                overall_status.write(
                    f"Completed {index + 1} of "
                    f"{len(selected_items)} files"
                )

            st.divider()

            st.subheader("Upload Summary")

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Selected",
                len(selected_items)
            )

            col2.metric(
                "Successful",
                successful
            )

            col3.metric(
                "Failed",
                failed
            )

            if failed == 0:

                st.success(
                    "All selected files uploaded successfully!"
                )

            else:

                st.warning(
                    "Some files failed. Check the error messages."
                )

        except Exception as error:

            st.error("Google Drive setup/upload process failed.")
            st.code(repr(error))
            st.code(traceback.format_exc(), language="text")
            traceback.print_exc()


elif chats:

    st.info(
        "Select a chat and click Browse Attachments."
    )


# -----------------------------------
# FOOTER
# -----------------------------------

st.divider()

st.caption(
    "Telegram Drive Manager | Concurrent Streaming Edition"
)