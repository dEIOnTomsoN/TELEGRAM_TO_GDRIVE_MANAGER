import os

from dotenv import load_dotenv
from google.auth.transport.requests import Request, AuthorizedSession
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/drive"
]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"

ROOT_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")


def get_drive_credentials():

    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    if not creds or not creds.valid:

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def get_drive_service():

    credentials = get_drive_credentials()

    return build(
        "drive",
        "v3",
        credentials=credentials
    )


def get_root_folder_id():

    if not ROOT_FOLDER_ID:
        raise ValueError(
            "GOOGLE_DRIVE_FOLDER_ID is missing from .env"
        )

    return ROOT_FOLDER_ID


def get_or_create_folder(service, folder_name, parent_id):

    escaped_name = (
        folder_name
        .replace("\\", "\\\\")
        .replace("'", "\\'")
    )

    query = (
        f"name='{escaped_name}' "
        "and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents "
        "and trashed=false"
    )

    result = service.files().list(
        q=query,
        fields="files(id,name)",
        pageSize=100
    ).execute()

    folders = result.get("files", [])

    if folders:
        return folders[0]["id"]

    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }

    created = service.files().create(
        body=metadata,
        fields="id,name"
    ).execute()

    return created["id"]


def create_resumable_upload(
    credentials,
    filename,
    folder_id,
    mime_type,
    file_size
):

    session = AuthorizedSession(credentials)

    url = (
        "https://www.googleapis.com/upload/drive/v3/files"
        "?uploadType=resumable"
    )

    metadata = {
        "name": filename,
        "parents": [folder_id]
    }

    response = session.post(
        url,
        json=metadata,
        headers={
            "X-Upload-Content-Type": mime_type,
            "X-Upload-Content-Length": str(file_size),
            "Content-Type": "application/json"
        },
        timeout=60
    )

    response.raise_for_status()

    upload_url = response.headers.get("Location")

    if not upload_url:
        raise RuntimeError(
            "Google Drive did not return an upload URL."
        )

    return session, upload_url


def upload_stream_chunk(
    session,
    upload_url,
    chunk,
    start,
    total_size
):

    end = start + len(chunk) - 1

    headers = {
        "Content-Length": str(len(chunk)),
        "Content-Range": (
            f"bytes {start}-{end}/{total_size}"
        )
    }

    response = session.put(
        upload_url,
        data=chunk,
        headers=headers,
        timeout=(60, 300)
    )

    if response.status_code == 308:
        return None

    if response.status_code in (200, 201):
        return response.json()

    response.raise_for_status()

    return None