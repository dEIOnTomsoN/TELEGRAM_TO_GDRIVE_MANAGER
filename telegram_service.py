import os
import re
import queue
import threading

from dotenv import load_dotenv
from telethon.sync import TelegramClient

from google_drive_service import (
    get_drive_credentials,
    create_resumable_upload,
    upload_stream_chunk
)

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = "telegram_session"

# Performance settings
CHUNK_SIZE = 8 * 1024 * 1024
TELEGRAM_REQUEST_SIZE = 512 * 1024
QUEUE_SIZE = 4

STOP = object()


def safe_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name or "")
    return name.strip(" .") or "telegram_file"


def get_telegram_chats():

    chats = []

    with TelegramClient(
        SESSION_NAME,
        API_ID,
        API_HASH
    ) as client:

        for dialog in client.iter_dialogs(limit=100):

            chats.append({
                "id": dialog.id,
                "name": dialog.name,
                "type": (
                    "Channel" if dialog.is_channel
                    else "Group" if dialog.is_group
                    else "Private Chat"
                ),
                "unread": dialog.unread_count
            })

    return chats


def classify_media(message):

    file = message.file

    if message.photo:
        return "Photo"

    mime = (file.mime_type or "").lower()
    filename = (file.name or "").lower()

    if mime.startswith("video/") or filename.endswith(
        (".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v")
    ):
        return "Video"

    if mime.startswith("image/") or filename.endswith(
        (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
    ):
        return "Photo"

    return "Document"


def get_chat_messages(chat_id, limit=50):

    attachments = []

    with TelegramClient(
        SESSION_NAME,
        API_ID,
        API_HASH
    ) as client:

        for message in client.iter_messages(
            chat_id,
            limit=limit
        ):

            if not message.media or not message.file:
                continue

            file = message.file
            media_type = classify_media(message)

            filename = file.name

            if not filename:

                extension = ""

                if file.mime_type and "/" in file.mime_type:
                    extension = "." + file.mime_type.split("/")[-1]

                filename = f"{media_type}_{message.id}{extension}"

            attachments.append({
                "message_id": message.id,
                "date": (
                    message.date.strftime("%d-%m-%Y %H:%M")
                    if message.date else ""
                ),
                "filename": safe_filename(filename),
                "type": media_type,
                "size": file.size or 0,
                "mime_type": (
                    file.mime_type or
                    "application/octet-stream"
                ),
                "chat_id": chat_id
            })

    return attachments


def stream_telegram_file_to_drive(
    chat_id,
    message_id,
    filename,
    mime_type,
    file_size,
    drive_folder_id,
    progress_callback=None
):
    """
    Concurrent Telegram-to-Google-Drive transfer.

    Telegram producer:
        Downloads media in small requests.

    Google Drive consumer:
        Uploads 8 MB chunks.

    Queue:
        Holds a maximum of four chunks.
    """

    if not file_size or file_size <= 0:
        raise ValueError("Invalid Telegram file size.")

    filename = safe_filename(filename)

    credentials = get_drive_credentials()

    session, upload_url = create_resumable_upload(
        credentials,
        filename,
        drive_folder_id,
        mime_type or "application/octet-stream",
        file_size
    )

    transfer_queue = queue.Queue(maxsize=QUEUE_SIZE)

    errors = []
    result = {}
    uploaded = [0]

    def uploader():

        position = 0
        upload_failed = False

        while True:

            chunk = transfer_queue.get()

            try:

                if chunk is STOP:
                    break

                # If an upload has failed, drain the queue
                # so the producer cannot deadlock.
                if upload_failed:
                    continue

                try:

                    response = upload_stream_chunk(
                        session,
                        upload_url,
                        chunk,
                        position,
                        file_size
                    )

                    position += len(chunk)
                    uploaded[0] = position

                    if response is not None:
                        result["file"] = response

                    if progress_callback:
                        progress_callback(
                            position,
                            file_size
                        )

                except Exception as error:

                    errors.append(error)
                    upload_failed = True

            finally:
                transfer_queue.task_done()

    worker = threading.Thread(
        target=uploader,
        name="GoogleDriveUploader",
        daemon=True
    )

    worker.start()

    buffer = bytearray()
    downloaded = 0

    try:

        with TelegramClient(
            SESSION_NAME,
            API_ID,
            API_HASH
        ) as client:

            message = client.get_messages(
                chat_id,
                ids=message_id
            )

            if not message or not message.media:
                raise ValueError(
                    "Telegram attachment not found."
                )

            for telegram_chunk in client.iter_download(
                message.media,
                request_size=TELEGRAM_REQUEST_SIZE
            ):

                if errors:
                    raise RuntimeError(
                        f"Google Drive upload failed: {errors[0]}"
                    )

                if not telegram_chunk:
                    continue

                buffer.extend(telegram_chunk)
                downloaded += len(telegram_chunk)

                while len(buffer) >= CHUNK_SIZE:

                    if errors:
                        raise RuntimeError(
                            f"Google Drive upload failed: {errors[0]}"
                        )

                    chunk = bytes(buffer[:CHUNK_SIZE])
                    del buffer[:CHUNK_SIZE]

                    transfer_queue.put(chunk)

            if downloaded != file_size:
                raise RuntimeError(
                    f"Telegram size mismatch: "
                    f"{downloaded} / {file_size} bytes."
                )

            if buffer:
                transfer_queue.put(bytes(buffer))
                buffer.clear()

    except Exception as error:

        errors.append(error)

    finally:

        # The worker drains remaining queued chunks before stopping.
        transfer_queue.put(STOP)

        transfer_queue.join()
        worker.join()

    if errors:
        raise RuntimeError(
            f"Transfer failed: {errors[0]}"
        ) from errors[0]

    if uploaded[0] != file_size:
        raise RuntimeError(
            f"Upload incomplete: "
            f"{uploaded[0]} / {file_size} bytes."
        )

    if not result.get("file"):
        raise RuntimeError(
            "Google Drive did not confirm upload completion."
        )

    return result["file"]