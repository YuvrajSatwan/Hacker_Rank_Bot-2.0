import requests
import os
import datetime
import random
import pytz
import sqlite3
import logging

# Configuration
TELEGRAM_BOT_TOKEN = "7211810846:AAFchPh2P70ZWlQPEH1WAVgaLxngvkHmz3A"
TELEGRAM_CHAT_ID = "1631288026"
GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAAABLlXXMM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=AxaA5jffPFX7ks0JXC4tGUkisYoSRvH8rv0BtX9xHBg"
CONTEST_SLUG = "peacemakers24b1"
DB_PATH = "/data/hackerrank_counts.db" if os.path.isdir("/data") else "hackerrank_counts.db"
HR_BASE_URL = f"https://www.hackerrank.com/contests/{CONTEST_SLUG}/challenges"

COOKIES = {
    "hackerrank_mixpanel_token": "2dab64b2-51e9-4c69-a1da-0014edcf9825",
    "peacemakers24b1_crp": "*nil*",
    "session_id": "0yhigm53-1740482754625",
    "user_type": "hacker",
    "_hrank_session": "ebfd03a3d3d948fd372abfe176cbb7f2",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

# Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Database Operations
def connect_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None

def setup_database():
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS tracker
                          (key TEXT PRIMARY KEY, value TEXT)"""
            )
            cursor.execute("INSERT OR IGNORE INTO tracker VALUES ('question_count', '0')")
            cursor.execute("INSERT OR IGNORE INTO tracker VALUES ('last_update', '')")
            cursor.execute("INSERT OR IGNORE INTO tracker VALUES ('no_questions_sent', '')")
            conn.commit()
            logging.info("Database setup complete.")
        except sqlite3.Error as e:
            logging.error(f"Database setup error: {e}")
        finally:
            conn.close()
    else:
        logging.error("Could not setup database due to connection failure.")

def get_db_value(key):
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM tracker WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logging.error(f"Database read error: {e}")
            return None
        finally:
            conn.close()
    else:
        logging.error("Could not get DB value due to connection failure.")
        return None

def set_db_value(key, value):
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO tracker VALUES (?, ?)", (key, str(value)))
            conn.commit()
            logging.info(f"Set database value: {key} = {value}")
        except sqlite3.Error as e:
            logging.error(f"Database write error: {e}")
        finally:
            conn.close()
    else:
        logging.error("Could not set DB value due to connection failure.")

# HackerRank Integration
def fetch_questions():
    offset = 0
    limit = 10
    all_questions = []
    try:
        while True:
            url = f"https://www.hackerrank.com/rest/contests/{CONTEST_SLUG}/challenges?offset={offset}&limit={limit}"
            response = requests.get(url, headers=HEADERS, cookies=COOKIES)
            if response.status_code != 200:
                logging.error(f"HackerRank API error: Status code {response.status_code}")
                return None, []
            data = response.json()
            questions = data.get("models", [])
            if not questions:
                break
            all_questions.extend([(q["name"], q["slug"]) for q in questions])
            offset += limit
        return len(all_questions), all_questions
    except (requests.exceptions.RequestException, ValueError) as e:
        logging.error(f"Error fetching questions: {e}")
        return None, []

def format_questions(questions, platform="telegram"):
    base_url = HR_BASE_URL
    formatted = []
    for name, slug in questions:
        if platform.lower() == "telegram":
            formatted.append(f"🔸<a href='{base_url}/{slug}'>{name}</a>")
        elif platform.lower() == "google_chat":
            formatted.append(f"🔸<{base_url}/{slug}|{name}>")
    return "\n".join(formatted)

# Notification System
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            logging.info("Telegram message sent successfully.")
        else:
            logging.error(f"Telegram API error: Status code {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Telegram Request Exception: {e}")

def send_google_chat_message(message):
    try:
        payload = {"text": message}
        response = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            logging.info("Google Chat message sent successfully.")
        else:
            logging.error(f"Google Chat API error: Status code {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Google Chat Request Exception: {e}")

# Core Logic
def notify_question_count():
    question_count, questions = fetch_questions()
    if question_count is None:
        logging.warning("Failed to fetch questions, skipping notification.")
        return

    last_count_raw = get_db_value("question_count")
    last_count = int(last_count_raw) if last_count_raw is not None and last_count_raw.isdigit() else 0
    logging.info(f"Last count: {last_count}, Current count: {question_count}")

    # Only notify if the count has changed
    if question_count != last_count:
        formatted_questions_telegram = format_questions(questions, "telegram")
        formatted_questions_google = format_questions(questions, "google_chat")

        notification_templates = [
            # Marvel
            f"""💥 *{question_count} CHALLENGES INCOMING!*  
"The hardest choices require the strongest wills." - Thanos (Infinity War)  
Your resolve shapes destiny.  
- *Targets:*  
{formatted_questions_telegram}  
Snap them out. Rule the ashes.""",

            f"""🔔 *{question_count} CHALLENGES DROP!*  
"I can do this all day." - Steve Rogers (Civil War)  
Endurance is your armor.  
- *Fight Zone:*  
{formatted_questions_telegram}  
Swing ‘til dawn. Never break.""",

            # Attack on Titan
            f"""🏰 *{question_count} CHALLENGES BREACH!*  
"If you win, you live. If you lose, you die." - Eren Yeager  
Survival’s the stakes.  
- *Walls:*  
{formatted_questions_telegram}  
Fight like hell. Live.""",

            f"""🏃 *{question_count} FOES ADVANCE!*  
"I’ll keep moving forward, until my enemies are destroyed." - Eren Yeager  
Momentum’s your blade.  
- *Path:*  
{formatted_questions_telegram}  
Charge. Erase.""",

            # Mixed Inspirational
            f"""⭐ *{question_count} CHALLENGES LAND!*  
"Do or do not. There is no try." - Yoda (The Empire Strikes Back)  
Full send or bust.  
- *Force:*  
{formatted_questions_telegram}  
Do it. Master.""",

            f"""⚔️ *{question_count} TRIALS RISE!*  
"What we do in life echoes in eternity." - Maximus (Gladiator)  
Make it echo.  
-.echo *Echo:*  
{formatted_questions_telegram}  
Fight loud. Live forever.""",
        ]

        selected_template = random.choice(notification_templates)
        telegram_msg = selected_template
        google_msg = selected_template.replace(formatted_questions_telegram, formatted_questions_google)

        send_telegram_message(telegram_msg)
        send_google_chat_message(google_msg)

        set_db_value("question_count", question_count)
        set_db_value("last_update", datetime.datetime.now().strftime("%Y-%m-%d"))
        logging.info(f"Question count updated from {last_count} to {question_count} and notification sent.")
    else:
        logging.info("No change in question count, no notification sent.")

def check_end_of_day():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)
    today = now.strftime("%Y-%m-%d")

    if now.hour >= 22 and (now.hour != 22 or now.minute >= 30):
        if get_db_value("last_update") != today and get_db_value("no_questions_sent") != today:
            eod_msg = f"""🌌 *Cosmic Calm Report*  
"The universe is under no obligation to make sense to you." - Neil deGrasse Tyson  
No new challenges today. Reality holds steady.  
☄️ Tomorrow’s wars await..."""
            send_telegram_message(eod_msg)
            send_google_chat_message(eod_msg)
            set_db_value("no_questions_sent", today)
            logging.info("End of day notification sent.")
        else:
            logging.info("End of day check skipped, already sent or updated today.")
    else:
        logging.info("End of day check skipped, not after 10:30 PM IST.")

if __name__ == "__main__":
    try:
        setup_database()
        notify_question_count()
        check_end_of_day()
    except Exception as e:
        logging.exception(f"An unhandled error occurred: {e}")
