import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Config
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

# Facebook & Instagram Config
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN', '')
import json
import os

FB_PAGE_ID = os.getenv('FB_PAGE_ID', '')
IG_ACCOUNT_ID = os.getenv('IG_ACCOUNT_ID', '')

ACCOUNTS_FILE = 'accounts.json'
def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    # Default fallback to .env if json doesn't exist
    default_accs = {
        'facebook': [{'name': 'Next Gen', 'id': FB_PAGE_ID}] if FB_PAGE_ID else [],
        'instagram': [{'name': 'sweetessence', 'id': IG_ACCOUNT_ID}] if IG_ACCOUNT_ID else []
    }
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(default_accs, f, indent=4)
    return default_accs

ACCOUNTS = load_accounts()

# YouTube Config
# Using OAuth 2.0 client secrets JSON file
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv('YOUTUBE_CLIENT_SECRETS_FILE', 'client_secrets.json')

# TikTok Config
TIKTOK_ACCESS_TOKEN = os.getenv('TIKTOK_ACCESS_TOKEN', '')
TIKTOK_OPEN_ID = os.getenv('TIKTOK_OPEN_ID', '')
