# Telegram to Google Drive Manager

<p align="center">
  <b>A Streamlit application to transfer Telegram media directly to Google Drive.</b>
</p>

<p align="center">
  Browse Telegram chats, select media files, and upload them to Google Drive using chunked streaming — without downloading the complete files to your local computer.
</p>

---

## About the Project

**Telegram to Google Drive Manager** is a Python-based web application built with Streamlit. It allows users to connect their Telegram account, browse chats and channels, identify media attachments, select files, and transfer them directly to Google Drive.

The application uses Telethon to retrieve Telegram media and the Google Drive API to upload files. Instead of storing entire files locally before uploading, it streams media in chunks to reduce local storage requirements.

## Key Features

- **Telegram Integration:** Connect to your Telegram account using the Telegram API.
- **Chat Browser:** View available Telegram chats and channels.
- **Media Detection:** Identify videos, photos, and documents in messages.
- **Media Filtering:** Filter files by Videos, Photos, Documents, or All.
- **Selective Upload:** Choose specific files for transfer.
- **Direct Streaming:** Transfer Telegram media to Google Drive without saving the complete file locally.
- **Chunked Transfers:** Process media in smaller data chunks.
- **Resumable Upload:** Use Google Drive resumable upload sessions.
- **Automatic Folder Organization:** Organize uploaded files by chat and media type.
- **Live Progress:** Monitor upload progress and status.
- **Background Processing:** Handle uploads separately while keeping the Streamlit interface responsive.
- **Error Handling:** Display upload failures and error information.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Streamlit | Web interface |
| Telethon | Telegram API integration |
| Google Drive API | Cloud file uploads |
| Google OAuth 2.0 | Google account authentication |
| Requests | HTTP resumable uploads |
| Threading | Background upload processing |
| Queue | Communication between upload worker and interface |

## Project Architecture

```text
TELEGRAM_TO_GDRIVE_MANAGER/
│
├── app.py
│   └── Streamlit application interface
│
├── telegram_service.py
│   └── Telegram authentication,
│       chat browsing and media streaming
│
├── google_drive_service.py
│   └── Google Drive authentication,
│       folder management and uploads
│
├── requirements.txt
│   └── Python dependencies
│
├── .env
│   └── Private API configuration
│
├── credentials.json
│   └── Google OAuth credentials
│
├── token.json
│   └── Google authentication token
│
├── telegram_session.session
│   └── Telegram login session
│
├── .gitignore
│   └── Excludes private and unnecessary files
│
└── README.md
    └── Project documentation
```

## How It Works

### 1. Connect to Telegram

The application uses Telethon and Telegram API credentials to authenticate the user.

After successful authentication, a local Telegram session is created for subsequent connections.

### 2. Browse Chats and Channels

The application retrieves available Telegram chats and channels. Users can select a chat and scan its recent messages for media attachments.

### 3. Identify and Select Media

The application identifies supported attachments:

- Videos
- Photos
- Documents

Users can filter the results and select the files they want to upload.

### 4. Connect to Google Drive

Google OAuth 2.0 is used to authorize access to the user's Google Drive account.

The application uses the Google Drive API to create folders and upload files to the selected destination.

### 5. Stream Files Directly

This is the main functionality of the project.

Instead of downloading an entire file to local storage, the application reads Telegram media progressively and transfers the data through a queue to the Google Drive upload worker.

The data is processed in chunks and sent using Google Drive resumable upload sessions.

### 6. Organize Files Automatically

Uploaded files are arranged into folders based on the Telegram chat and media category.

Example folder structure:

```text
Google Drive/
│
└── BB M D3/
    │
    ├── Telegram Chat/
    │   ├── Videos/
    │   ├── Photos/
    │   └── Documents/
    │
    └── Another Chat/
        ├── Videos/
        ├── Photos/
        └── Documents/
```

### 7. Monitor Uploads

The application displays upload progress and transfer status.

A queue is used to communicate progress updates from the background worker to the main Streamlit interface. This avoids updating Streamlit UI elements directly from a background thread.

## Installation and Setup

### Prerequisites

Make sure you have:

- Python 3.10 or newer
- Git
- A Telegram account
- Telegram API credentials
- A Google account
- A Google Cloud project with Google Drive API enabled

### Step 1: Clone the Repository

```bash
git clone https://github.com/dEIOnTomsoN/TELEGRAM_TO_GDRIVE_MANAGER.git
```

Navigate to the project directory:

```bash
cd TELEGRAM_TO_GDRIVE_MANAGER
```

### Step 2: Create a Virtual Environment

```bash
python -m venv venv
```

Activate it on Windows:

```powershell
.\venv\Scripts\activate
```

For Linux or macOS:

```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Telegram API

1. Visit https://my.telegram.org
2. Log in with your Telegram account.
3. Open **API Development Tools**.
4. Create an application.
5. Copy your API ID and API Hash.

### Step 5: Configure Google Drive API

1. Visit https://console.cloud.google.com/
2. Create a Google Cloud project.
3. Enable the Google Drive API.
4. Configure the OAuth consent screen.
5. Create an OAuth Client ID.
6. Select **Desktop App** as the application type.
7. Download the OAuth credentials.
8. Save the downloaded file as `credentials.json` in the project directory.

If your OAuth application is in Testing mode, add your Google account as a test user.

### Step 6: Configure Environment Variables

Create a `.env` file in the project directory.

Add the following configuration:

```env
API_ID=YOUR_TELEGRAM_API_ID
API_HASH=YOUR_TELEGRAM_API_HASH
PHONE=YOUR_TELEGRAM_PHONE_NUMBER

GOOGLE_DRIVE_FOLDER_ID=YOUR_GOOGLE_DRIVE_FOLDER_ID
```

Replace the placeholder values with your actual credentials and destination folder ID.

**Never upload your `.env` file or authentication credentials to GitHub.**

### Step 7: Run the Application

```bash
streamlit run app.py
```

Open the application in your browser:

```text
http://localhost:8501
```

## Upload Workflow

```text
       Telegram Account
              |
              v
       Browse Chats
              |
              v
       Scan Messages
              |
              v
       Detect Attachments
              |
              v
       Filter and Select Files
              |
              v
       Read Telegram Media
              |
              v
       Stream Data in Chunks
              |
              v
       Google Drive Upload
              |
              v
       Organize Files into Folders
              |
              v
       Display Upload Status
```

## Storage and Performance

The application follows a streaming-based transfer approach.

- Does not intentionally save the complete media file locally.
- Uses chunk-based data processing.
- Uses a queue to manage communication between the download and upload processes.
- Uses Google Drive resumable upload sessions.
- Uses background processing to keep the interface responsive.

Transfer performance depends on the internet connection, Telegram download speed, Google Drive upload speed, and available system resources.

## Security and Privacy

This project requires access to personal Telegram and Google accounts.

The following files contain sensitive information and must not be committed to GitHub:

```text
.env
credentials.json
token.json
*.session
*.session-journal
```

The project includes a `.gitignore` file to exclude private credentials, session files, virtual environments, and temporary downloads.

**Important:** Never share your Telegram session file, Google OAuth tokens, API Hash, or other private credentials.

## Limitations

- The computer must remain powered on while running the local application.
- An active internet connection is required during transfers.
- Telegram and Google authentication must be configured correctly.
- Upload speed depends on network conditions and service limitations.
- Interrupted uploads may require retrying; automatic recovery is not guaranteed.

## Future Enhancements

- Android mobile application.
- Upload history and transfer logs.
- Automatic retry for failed uploads.
- Improved pause and resume functionality.
- Multiple upload management.
- Upload speed monitoring.
- Custom Google Drive destination folders.
- Improved mobile-friendly interface.

## Author

**Deion Tomson**

Computer Science and Engineering Graduate

- GitHub: https://github.com/dEIOnTomsoN
- Project Repository: https://github.com/dEIOnTomsoN/TELEGRAM_TO_GDRIVE_MANAGER

---


---

<p align="center">
  <b>Telegram → Google Drive</b><br>
  Transfer your files without storing the complete files locally.
</p>