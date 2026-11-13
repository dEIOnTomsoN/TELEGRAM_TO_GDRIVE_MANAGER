
import os
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")

SESSION_NAME = "telegram_session"

if not API_ID or not API_HASH or not PHONE:
    raise ValueError("Check your Telegram credentials in .env")

client = TelegramClient(
    SESSION_NAME,
    API_ID,
    API_HASH
)

try:
    client.connect()

    if not client.is_user_authorized():

        print("\nSending Telegram login code...")

        result = client.send_code_request(PHONE)

        print("Login code sent to your Telegram account.")

        code = input("Enter your Telegram verification code: ").strip()

        try:
            client.sign_in(
                phone=PHONE,
                code=code,
                phone_code_hash=result.phone_code_hash
            )

        except SessionPasswordNeededError:

            password = input(
                "Enter your Telegram two-step verification password: "
            )

            client.sign_in(password=password)

    me = client.get_me()

    print("\n================================")
    print("TELEGRAM CONNECTED SUCCESSFULLY")
    print("================================")
    print("Name:", me.first_name)
    print("Username:", me.username)
    print("User ID:", me.id)
    print("Session saved locally.")

except Exception as error:
    print("\nTelegram connection failed:")
    print(str(error))

finally:
    client.disconnect()
