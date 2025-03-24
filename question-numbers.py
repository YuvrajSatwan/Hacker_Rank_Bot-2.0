import requests
import os
import datetime
import random
import pytz
import sqlite3
import logging
import json

# Configuration
TELEGRAM_BOT_TOKEN = "7211810846:AAFchPh2P70ZWlQPEH1WAVgaLxngvkHmz3A"
TELEGRAM_CHAT_ID = "1631288026"
GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAAABLlXXMM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=AxaA5jffPFX7ks0JXC4tGUkisYoSRvH8rv0BtX9xHBg"
CONTEST_SLUG = "peacemakers24b1"
DB_PATH = "hackerrank_counts.db"
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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
            cursor.execute("INSERT OR IGNORE INTO tracker VALUES ('question_slugs', '[]')")
            cursor.execute("INSERT OR IGNORE INTO tracker VALUES ('last_update', '')")
            cursor.execute("INSERT OR IGNORE INTO tracker VALUES ('no_questions_sent', '')")
            conn.commit()
            logging.info("Database setup complete.")
        except sqlite3.Error as e:
            logging.error(f"Database setup error: {e}")
        finally:
            conn.close()
            def initialize_database_if_empty():
    last_slugs_raw = get_db_value("question_slugs")
    # Force reset for testing (comment out after one run)
    last_slugs = []
    if not last_slugs_raw or last_slugs == []:
        _, questions = fetch_questions(120)
        if questions:
            real_slugs = [q[1] for q in questions]
            set_db_value("question_slugs", json.dumps(real_slugs))
            set_db_value("last_update", "2025-03-24")
            logging.info(f"Initialized database with 120 real questions: {real_slugs[:5]}...")

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
        logging.info(f"Fetched {len(all_questions)} questions from API.")
        return len(all_questions), all_questions
    except (requests.exceptions.RequestException, ValueError) as e:
        logging.error(f"Error fetching questions: {e}")
        return None, []

def format_questions(questions, platform="telegram", max_questions=10):
    base_url = HR_BASE_URL
    formatted = []
    for i, (name, slug) in enumerate(questions[:max_questions]):
        if platform.lower() == "telegram":
            formatted.append(f"✨ <a href='{base_url}/{slug}'>{name}</a>")
        elif platform.lower() == "google_chat":
            formatted.append(f"✨ <{base_url}/{slug}|{name}>")
    if len(questions) > max_questions:
        formatted.append(f"...and {len(questions) - max_questions} more!")
    return "\n".join(formatted)

def send_telegram_message(message):
    logging.info(f"Telegram message preview: {message[:100]}...")
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
    logging.info(f"Google Chat message preview: {message[:100]}...")
    try:
        payload = {"text": message}
        response = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json=payload)
        if response.status_code == 200:
            logging.info("Google Chat message sent successfully.")
        else:
            logging.error(f"Google Chat API error: Status code {response.status_code}, Response: {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Google Chat Request Exception: {e}")

def notify_question_count():
    question_count, questions = fetch_questions()
    if question_count is None:
        logging.warning("Failed to fetch questions, skipping notification.")
        return

    last_slugs_raw = get_db_value("question_slugs")
    try:
        last_slugs = json.loads(last_slugs_raw) if last_slugs_raw else []
        if not isinstance(last_slugs, list):
            raise ValueError("last_slugs is not a list")
    except (json.JSONDecodeError, ValueError) as e:
        logging.warning(f"Failed to parse last_slugs ({e}), defaulting to empty list.")
        last_slugs = []
    logging.info(f"Previous slugs count: {len(last_slugs)}, sample: {last_slugs[:5]}...")

    current_slugs = [q[1] for q in questions]
    logging.info(f"Current slugs count: {len(current_slugs)}, sample: {current_slugs[:5]}...")

    new_slugs = [slug for slug in current_slugs if slug not in last_slugs]
    new_questions = [q for q in questions if q[1] in new_slugs]
    logging.info(f"New slugs found: {len(new_slugs)}, list: {new_slugs}")

    # Print names of new questions
    if new_questions:
        print("New Questions Detected:")
        for name, slug in new_questions:
            print(f"- {name}")
    else:
        print("No new questions found.")

    if new_questions:
        formatted_questions_telegram = format_questions(new_questions, "telegram", max_questions=10)
        formatted_questions_google = format_questions(new_questions, "google_chat", max_questions=10)

        notification_templates = [
            f"🔥 {len(new_questions)} new coding challenge just arrived! Will you be the first to solve them? ⚡\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"💡 {len(new_questions)} fresh problem are waiting for you. Time to showcase your skills! 🚀\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"⚔️ A new war begins! {len(new_questions)} more puzzle to crack. Are you the coding champion? 👑\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🤖 {len(new_questions)} fresh problem have dropped! Will you rise or fall? The battle is on! 🔥\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"⏳ Time waits for none! {len(new_questions)} new question are here. Ready to claim your rank? 🏆\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🚀 A new era begins... {len(new_questions)} fresh challenge have arrived. Will you rise to the occasion? ⚔️🔥\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🧠 The battle of minds ignites! {len(new_questions)} new problem await. Who will claim victory? 🏆\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"⚡ Anomaly detected! {len(new_questions)} new coding puzzle have surfaced. Time to decode the unknown! 🤖\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🌌 The void shifts... {len(new_questions)} challenge have emerged. Only the worthy will conquer them! ⚔️\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🛡️ A warrior’s path is never easy! {len(new_questions)} new trials have been unleashed. Face them with courage! 💡\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"⏳ Time waits for no one! {len(new_questions)} more problem stand between you and greatness. Will you take them on? 🏅\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"📜 A new scroll has been uncovered! The secrets within these {len(new_questions)} question are waiting for a true solver! 🔍\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"💥 The battlefield roars! {len(new_questions)} new coding quest have arrived. Show the world your skills! 🌟\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"new challenges... {len(new_questions)} coding mystery await. Will you solve them before anyone else? ⚙️\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🕵️ A secret has been unveiled... {len(new_questions)} fresh problem are here. The hunt for solutions begins now! 🔥\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🌌 {len(new_questions)} challenges emerge from the dark. 'The hardest choices require the strongest wills.' - Thanos. Shape your fate with every solution.\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"⚡ {len(new_questions)} trials awaken. 'I can do this all day.' - Captain America. Persistence carves the path to greatness.\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🛡️ {len(new_questions)} quests stand before you. 'With great power comes great responsibility.' - Uncle Ben. Wield your intellect to rise.\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🔥 {len(new_questions)} enigmas ignite the horizon. 'Why do we fall? So we can learn to pick ourselves up.' - Alfred. Each step builds your strength.\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🌠 {len(new_questions)} puzzles call your name. 'I am Iron Man.' - Tony Stark. Craft your legacy through every line of code.\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"⚙️ {len(new_questions)} tests of will arise. 'It’s not who I am underneath, but what I do that defines me.' - Batman. Let your actions speak.\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"⏳ {len(new_questions)} challenges mark this moment. 'Whatever it takes.' - Avengers. Sacrifice today for triumph tomorrow.\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🗡️ {len(new_questions)} battles demand your focus. 'There is only one god, and his name is Death.' - Wonder Woman. Conquer them with unrelenting clarity.\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"💡 {len(new_questions)} riddles test your soul. 'I’m vengeance.' - Batman. Strike through the shadows with precision.\n\n📌 New Questions:\n{formatted_questions_telegram}",
            f"🌍 {len(new_questions)} trials shift the balance. 'Perfectly balanced, as all things should be.' - Thanos. Restore order with your mastery.\n\n📌 New Questions:\n{formatted_questions_telegram}"
        ]

        if last_slugs_raw is None:  # Truly first run
            telegram_msg = f"🚀 First Check! {question_count} questions are live!\n\n📌 **Latest Questions:**\n{format_questions(questions, 'telegram')}"
            google_msg = f"🚀 First Check! {question_count} questions are live!\n\n📌 **Latest Questions:**\n{format_questions(questions, 'google_chat')}"
        else:
            selected_template = random.choice(notification_templates)
            telegram_msg = selected_template
            google_msg = selected_template.replace(formatted_questions_telegram, formatted_questions_google)

        send_telegram_message(telegram_msg)
        send_google_chat_message(google_msg)

        set_db_value("question_slugs", json.dumps(current_slugs))
        set_db_value("last_update", datetime.datetime.now().strftime("%Y-%m-%d"))
        logging.info(f"Found {len(new_questions)} new questions. Notification sent.")
    else:
        logging.info("No new questions found, no notification sent.")

def check_end_of_day():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)
    today = now.strftime("%Y-%m-%d")

    if now.hour >= 22 and (now.hour != 22 or now.minute >= 30):
        if get_db_value("last_update") != today and get_db_value("no_questions_sent") != today:
            eod_messages = [
                "🕰️ The battlefield remained quiet today. But remember, the real warriors sharpen their blades in silence. ⚔️🔥",
                "🤖 No new challenges today, but legends never rest. Stay sharp, for the storm may arrive tomorrow! ⚡",
                "⏳ A day without new battles... The silence before the storm? Stay alert, coder! 🚀",
                "🌓 The coding universe is quiet tonight. Perhaps a challenge awaits at dawn? Be ready! 🌅",
                "💭 Today, the servers rest. The future awaits! 🚀",
                "🚀 The best coders don't wait for challenges... They create their own battles in silence. Did you grind today?",
                "💪 Today's silence is tomorrow's victory... Every line of code you write in the shadows will echo in the leaderboard!",
                "🌑 No questions today... but the battlefield isn't empty — it's waiting for the few who are hungry enough to train in the silence.",
                "🔥 Legends aren't made on the leaderboard... they are built in the days no one is watching. What will you build today?",
                "⏳ A day without challenges is not a rest day... It's a test of **who trains even when the battlefield is empty.**",
                "💭 The Void is silent today... but the real warriors never wait for orders. They grind in the shadows.",
                "👀 The leaderboard doesn't see what you do in silence... but it will one day remember your name.",
                "⚡ A day without battles is a blessing... Because the greatest warriors sharpen their blades when the world sleeps.",
                "🚶‍♂️ One day, the leaderboard will call your name... But only if you walk the path when no one is watching.",
                "🔒 No new challenges today... That's not an excuse — it's an invitation to outwork everyone silently.",
                "🌘 The Void may be empty... but every line of code you write in this silence is one step closer to the 1% Club.",
                "🔥 The difference between 99% and 1%? What you do when there are no new battles to fight.",
                "⚔️ The leaderboard is sleeping... but the VoidWalkers are still grinding. Are you one of them?",
                "🌑 Today the battlefield is empty... But the rise of warriors always begins in the shadows.",
                "💀 Real coders fear comfort more than failure. Did you grind today, or did you rest with the 99%?",
                "🚀 Zero questions = Zero excuses. If the world isn't testing you... test yourself.",
                "🔄 No new questions... But consistency beats talent when talent is sleeping.",
                "⚡ The leaderboard will remember your name... but only if you grind in the days no one sees.",
                "💪 A silent day is the best day... because that's when only the real ones keep coding.",
                "📜 One empty day will never break a legend... but one skipped day might.",
                "🔥 No new questions... But there's always one unsolved problem — the one inside your own mind.",
                "⚔️ The journey is not about coding every day... it's about becoming the kind of person who codes every day."
            ]
            eod_msg = random.choice(eod_messages)
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
        # check_end_of_day()
    except Exception as e:
        logging.exception(f"An unhandled error occurred: {e}")
