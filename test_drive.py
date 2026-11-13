from google_drive_service import get_drive_service
import os

from dotenv import load_dotenv

load_dotenv()

FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

try:
    print("Connecting to Google Drive...")

    service = get_drive_service()

    folder = service.files().get(
        fileId=FOLDER_ID,
        fields="id,name,mimeType"
    ).execute()

    print("\nGOOGLE DRIVE CONNECTED SUCCESSFULLY")
    print("Folder Name:", folder["name"])
    print("Folder ID:", folder["id"])
    print("Folder Type:", folder["mimeType"])

except Exception as error:
    print("\nGOOGLE DRIVE CONNECTION FAILED")
    print(error)