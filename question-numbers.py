import requests
import os
import datetime
import random
import pytz
import sqlite3
import time

# Credentials
TELEGRAM_BOT_TOKEN = "7211810846:AAFchPh2P70ZWlQPEH1WAVgaLxngvkHmz3A"
TELEGRAM_CHAT_ID = "1631288026"
GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAAABLlXXMM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=AxaA5jffPFX7ks0JXC4tGUkisYoSRvH8rv0BtX9xHBg"

# SQLite path
DB_PATH = "/data/hackerrank_counts.db" if os.path.exists("/data") else "hackerrank_counts.db"

# HackerRank config
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
CONTEST_SLUG = "peacemakers24b1"

def connect_db():
    print("DEBUG: Connecting to database")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    return conn, cursor

def setup_database():
    print("DEBUG: Setting up database")
    conn, cursor = connect_db()
    cursor.execute("CREATE TABLE IF NOT EXISTS tracker (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT OR IGNORE INTO tracker (key, value) VALUES ('question_count', '0')")
    cursor.execute("INSERT OR IGNORE INTO tracker (key, value) VALUES ('last_update', '')")
    cursor.execute("INSERT OR IGNORE INTO tracker (key, value) VALUES ('no_questions_sent', '')")
    conn.commit()
    conn.close()

def get_db_value(key):
    print(f"DEBUG: Getting value for {key}")
    conn, cursor = connect_db()
    cursor.execute("SELECT value FROM tracker WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_db_value(key, value):
    print(f"DEBUG: Setting {key} = {value}")
    conn, cursor = connect_db()
    cursor.execute("INSERT OR REPLACE INTO tracker (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def fetch_questions():
    print("DEBUG: Fetching questions")
    offset = 0
    limit = 10
    all_questions = []
    while True:
        url = f"https://www.hackerrank.com/rest/contests/{CONTEST_SLUG}/challenges?offset={offset}&limit={limit}&track_login=true"
        response = requests.get(url, headers=HEADERS, cookies=COOKIES)
        if response.status_code == 200:
            data = response.json()
            questions = data.get("models", [])
            if not questions:
                break
            for question in questions:
                all_questions.append(question["name"])
            offset += limit
        else:
            print(f"❌ Request Failed! Status Code: {response.status_code}")
            return None, []
    return len(all_questions), all_questions

def send_telegram_message(message):
    print("DEBUG: Sending Telegram message")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    response = requests.post(url, data=data)
    print("✅ Telegram notification sent!" if response.status_code == 200 else 
          f"❌ Telegram failed: {response.status_code}, {response.text}")

def send_google_chat_message(message):
    print("DEBUG: Sending Google Chat message")
    response = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json={"text": message})
    print("✅ Google Chat notification sent!" if response.status_code == 200 else 
          f"❌ Google Chat failed: {response.status_code}, {response.text}")

def notify_question_count():
    print("DEBUG: Starting notify_question_count")
    question_count, question_names = fetch_questions()
    if question_count is None:
        print("❌ Failed to fetch questions.")
        return

    last_count = int(get_db_value("question_count") or 0)

    if last_count == 0:
        message = f"🚀 First Check! {question_count} questions are live!\n\n📌 **Latest Questions:**\n" + "\n".join([f"🔹 {q}" for q in question_names])
    else:
        difference = question_count - last_count
        if difference > 0:
            new_questions = question_names[-difference:]
            messages = [
                f"🔥 {difference} new coding challenge just arrived! Will you be the first to solve them? ⚡",
                f"💡 {difference} fresh problem are waiting for you. Time to showcase your skills! 🚀",
            ]
            message = f"{random.choice(messages)}\n\n📌 New Questions:\n" + "\n".join([f"✨ {q}" for q in new_questions])
            send_telegram_message(message)
            send_google_chat_message(message)
        else:
            print("No new questions. Skipping notification.")
            return

    set_db_value("question_count", question_count)
    set_db_value("last_update", datetime.datetime.now().strftime("%Y-%m-%d"))

def check_end_of_day():
    print("DEBUG: Starting check_end_of_day")
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_time = utc_now.astimezone(pytz.timezone("Asia/Kolkata"))
    today_date = ist_time.strftime("%Y-%m-%d")

    if (ist_time.hour > 22 or (ist_time.hour == 22 and ist_time.minute >= 30)):
        last_update_date = get_db_value("last_update")
        no_questions_sent_date = get_db_value("no_questions_sent")

        if last_update_date != today_date and no_questions_sent_date != today_date:
            messages = [
                "🕰️ The battlefield remained quiet today. But remember, the real warriors sharpen their blades in silence. ⚔️🔥",
            ]
            message = random.choice(messages)
            send_telegram_message(message)
            send_google_chat_message(message)
            set_db_value("no_questions_sent", today_date)
    else:
        print("Time is not yet 10:30 PM IST.")

if __name__ == "__main__":
    print("DEBUG: Bot starting")
    while True:
        try:
            setup_database()
            notify_question_count()
            check_end_of_day()
            print("DEBUG: Sleeping for 5 minutes")
            time.sleep(300)
        except Exception as e:
            print(f"ERROR: Bot crashed with {str(e)}")
            time.sleep(10)  # Wait before retrying
