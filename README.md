# NoxStage1 Bot

## Features
- /start with language selection (Russian/English)
- Main menu: Menu, Book table, Leave review
- Booking dialog: zone, table, datetime, people
- Notifications to Telegram group
- In-memory seats and user data (for testing)

## Setup
1. Copy `.env.example` to `.env` and fill in BOT_TOKEN and GROUP_CHAT_ID
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run bot:
   ```
   python main.py
   ```