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
            if result:
                return result[0]
            else:
                return None
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

            try:
                data = response.json()
                questions = data.get("models", [])
                if not questions:
                    break

                all_questions.extend([(q["name"], q["slug"]) for q in questions])
                offset += limit
            except ValueError as e:
                logging.error(f"JSON decode error: {e}")
                return None, []

        return len(all_questions), all_questions
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Exception: {e}")
        return None, []

def format_questions(questions, platform="telegram"):
    """Format questions with platform-specific links for Telegram and Google Chat."""
    base_url = f"{HR_BASE_URL}"
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
        if response.status_code != 200:
            logging.error(f"Telegram API error: Status code {response.status_code}, Response: {response.text}")
        else:
            logging.info("Telegram message sent successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Telegram Request Exception: {e}")

def send_google_chat_message(message):
    """Send message to Google Chat with simplified text format."""
    try:
        payload = {"text": message}
        logging.info(f"Sending Google Chat message: {message[:100]}...")
        response = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json=payload)
        if response.status_code != 200:
            logging.error(f"Google Chat API error: Status code {response.status_code}, Response: {response.text}")
        else:
            logging.info("Google Chat message sent successfully.")
    except requests.exceptions.RequestException as e:
        logging.error(f"Google Chat Request Exception: {e}")

# Core Logic
def notify_question_count():
    question_count, questions = fetch_questions()
    if question_count is None:
        logging.warning("Failed to fetch questions, skipping notification.")
        return

    last_count_raw = get_db_value("question_count")
    last_count = int(last_count_raw) if last_count_raw is not None else 0
    logging.info(f"Last count: {last_count}, Current count: {question_count}")

    formatted_questions_telegram = format_questions(questions, "telegram")
    formatted_questions_google = format_questions(questions, "google_chat")

    # Always send a random epic message
    notification_templates = [
        # Marvel
        f"""💥 *{question_count} CHALLENGES INCOMING!*  
_*"The hardest choices require the strongest wills." - Thanos (Infinity War)*_  
Your resolve shapes destiny.  
- *Targets:*  
{formatted_questions_telegram}  
Snap them out. Rule the ashes.""",

        f"""🔔 *{question_count} CHALLENGES DROP!*  
_*"I can do this all day." - Steve Rogers (Civil War)*_  
Endurance is your armor.  
- *Fight Zone:*  
{formatted_questions_telegram}  
Swing ‘til dawn. Never break.""",

        f"""🔴 *{question_count} TARGETS LOCKED!*  
_*"I’m not locked in here with you. You’re locked in here with me." - Tony Stark (Iron Man)*_  
You’re the hunter.  
- *Prey List:*  
{formatted_questions_telegram}  
Strike fast. Genius wins.""",

        f"""🌩️ *{question_count} CHALLENGES RISE!*  
_*"Whatever it takes." - Avengers (Endgame)*_  
Victory demands all.  
- *Mission Brief:*  
{formatted_questions_telegram}  
Give it. Take it. No less.""",

        f"""💀 *{question_count} FOES UNLEASHED!*  
_*"We have a Hulk." - Tony Stark (The Avengers)*_  
Rage is your edge.  
- *Smash Targets:*  
{formatted_questions_telegram}  
Crush them. Leave rubble.""",

        f"""⚙️ *{question_count} TRIALS IGNITE!*  
_*"I am Iron Man." - Tony Stark (Iron Man)*_  
You’re the spark.  
- *Your Forge:*  
{formatted_questions_telegram}  
Build it. Claim it.""",

        f"""🕷️ *{question_count} CHALLENGES LAND!*  
_*"With great power comes great responsibility." - Uncle Ben (Spider-Man)*_  
Power’s yours to wield.  
- *Web of Duty:*  
{formatted_questions_telegram}  
Rise up. Own it.""",

        # DC
        f"""🌙 *{question_count} CHALLENGES STRIKE!*  
_*"I’m not a hero. I’m a high-functioning disaster." - Batman (The Dark Knight, paraphrased)*_  
Chaos fuels you.  
- *Shadows:*  
{formatted_questions_telegram}  
Burn the night. Win the day.""",

        f"""⚖️ *{question_count} TESTS DESCEND!*  
_*"It’s not who I am underneath, but what I do that defines me." - Batman (Batman Begins)*_  
Deeds are your voice.  
- *Proof:*  
{formatted_questions_telegram}  
Act now. Be heard.""",

        f"""🦇 *{question_count} FOES RISE!*  
_*"Why do we fall? So we can learn to pick ourselves up." - Alfred (Batman Begins)*_  
Every fall’s a lesson.  
- *Ascent:*  
{formatted_questions_telegram}  
Rise stronger. Dominate.""",

        f"""🌌 *{question_count} TRIALS EMERGE!*  
_*"I am vengeance. I am the night." - Batman (Batman: The Animated Series)*_  
You’re their nightmare.  
- *Justice:*  
{formatted_questions_telegram}  
Strike swift. End them.""",

        f"""☀️ *{question_count} CHALLENGES CALL!*  
_*"The world only makes sense if you force it to." - Superman (Man of Steel, paraphrased)*_  
Bend it to your will.  
- *Order:*  
{formatted_questions_telegram}  
Shape it. Rule it.""",

        # Game of Thrones
        f"""👑 *{question_count} CHALLENGES MARCH!*  
_*"When you play the game of thrones, you win or you die." - Cersei Lannister*_  
Crown or grave.  
- *Throne Room:*  
{formatted_questions_telegram}  
Take it. Reign.""",

        f"""🔥 *{question_count} FOES APPROACH!*  
_*"The night is dark and full of terrors." - Melisandre*_  
You’re the dawn.  
- *Light:*  
{formatted_questions_telegram}  
Burn them out. Shine.""",

        f"""🌊 *{question_count} BATTLES BEGIN!*  
_*"I am the storm, my lord. The first storm and the last." - Euron Greyjoy*_  
You’re the tempest.  
- *Fury:*  
{formatted_questions_telegram}  
Wreck them. Reign.""",

        f"""🦁 *{question_count} TESTS ARRIVE!*  
_*"A lion does not concern himself with the opinions of sheep." - Tywin Lannister*_  
You’re the predator.  
- *Dominion:*  
{formatted_questions_telegram}  
Roar. Feast.""",

        f"""❄️ *{question_count} CHALLENGES DROP!*  
_*"Winter is coming." - Ned Stark*_  
Steel yourself.  
- *Defense:*  
{formatted_questions_telegram}  
Stand firm. Thrive.""",

        # Attack on Titan
        f"""🏰 *{question_count} CHALLENGES BREACH!*  
_*"If you win, you live. If you lose, you die." - Eren Yeager*_  
Survival’s the stakes.  
- *Walls:*  
{formatted_questions_telegram}  
Fight like hell. Live.""",

        f"""🏃 *{question_count} FOES ADVANCE!*  
_*"I’ll keep moving forward, until my enemies are destroyed." - Eren Yeager*_  
Momentum’s your blade.  
- *Path:*  
{formatted_questions_telegram}  
Charge. Erase.""",

        f"""🕊️ *{question_count} TRIALS LOOM!*  
_*"We’re born free. All of us." - Erwin Smith*_  
Freedom’s your birthright.  
- *Liberty:*  
{formatted_questions_telegram}  
Earn it. Break free.""",

        f"""❤️ *{question_count} CHALLENGES ATTACK!*  
_*"Dedicate your hearts!" - Erwin Smith*_  
All in or nothing.  
- *Sacrifice:*  
{formatted_questions_telegram}  
Give it. Win it.""",

        f"""⚔️ *{question_count} BATTLES RAGE!*  
_*"This world is cruel, and yet so beautiful." - Mikasa Ackerman*_  
Beauty’s in the struggle.  
- *War:*  
{formatted_questions_telegram}  
Make it yours. Triumph.""",

        # Jujutsu Kaisen
        f"""👹 *{question_count} CURSES SPAWN!*  
_*"I’ll kill you with my own hands." - Yuji Itadori*_  
Raw power’s yours.  
- *Targets:*  
{formatted_questions_telegram}  
Rip them apart. No mercy.""",

        f"""🌌 *{question_count} CHALLENGES UNLEASH!*  
_*"I’m not here to lose." - Satoru Gojo*_  
Defeat’s not an option.  
- *Domain:*  
{formatted_questions_telegram}  
Control it. Win it.""",

        f"""🐺 *{question_count} FOES RISE!*  
_*"Technique alone won’t win this." - Megumi Fushiguro*_  
Guts seal the deal.  
- *Shadows:*  
{formatted_questions_telegram}  
Summon it. Crush.""",

        f"""⚡ *{question_count} TRIALS DROP!*  
_*"I’ll show you what real jujutsu is." - Satoru Gojo*_  
You’re the master.  
- *Art:*  
{formatted_questions_telegram}  
Teach them. End them.""",

        f"""⏰ *{question_count} CHALLENGES IGNITE!*  
_*"No regrets." - Nanami Kento*_  
Forward only.  
- *Duty:*  
{formatted_questions_telegram}  
Cut through. Move on.""",

        # The 48 Laws of Power
        f"""🎭 *{question_count} CHALLENGES EMERGE!*  
_*"Never outshine the master." - Law 1*_  
But eclipse your foes.  
- *Power:*  
{formatted_questions_telegram}  
Steal the light. Rule.""",

        f"""🗡️ *{question_count} TESTS STRIKE!*  
_*"Win through actions, never through argument." - Law 9*_  
Deeds are your crown.  
- *Proof:*  
{formatted_questions_telegram}  
Act. Reign.""",

        f"""💣 *{question_count} FOES CHALLENGE!*  
_*"Crush your enemy totally." - Law 15*_  
No remnants. Total victory.  
- *Victory:*  
{formatted_questions_telegram}  
Obliterate. Rise.""",

        f"""🕵️ *{question_count} BATTLES BEGIN!*  
_*"Pose as a friend, work as a spy." - Law 14*_  
Knowledge is your blade.  
- *Deception:*  
{formatted_questions_telegram}  
Outsmart. Outlast.""",

        f"""👑 *{question_count} CHALLENGES CALL!*  
_*"Play on people’s need to believe to create a cultlike following." - Law 27*_  
They’ll chant your name.  
- *Legion:*  
{formatted_questions_telegram}  
Inspire. Conquer.""",

        # The Subtle Art of Not Giving a F*ck
        f"""💀 *{question_count} CHALLENGES HIT!*  
_*"You’re going to die one day." - Mark Manson*_  
So fight like it’s now.  
- *Life:*  
{formatted_questions_telegram}  
Make it epic. Go.""",

        f"""🚫 *{question_count} TESTS DROP!*  
_*"The only way to be comfortable with failure is to fail more." - Mark Manson*_  
Fail fast. Win big.  
- *Growth:*  
{formatted_questions_telegram}  
Fall. Soar.""",

        f"""👊 *{question_count} FOES ARRIVE!*  
_*"Life is a series of problems. Pick good ones." - Mark Manson*_  
These are yours.  
- *Choice:*  
{formatted_questions_telegram}  
Solve them. Win.""",

        f"""🔇 *{question_count} CHALLENGES IGNITE!*  
_*"Stop giving a fuck about what doesn’t matter." - Mark Manson*_  
Focus is your weapon.  
- *Focus:*  
{formatted_questions_telegram}  
Cut the crap. Strike.""",

        f"""😊 *{question_count} TRIALS RISE!*  
_*"Happiness comes from solving problems." - Mark Manson*_  
Joy’s in the grind.  
- *Reward:*  
{formatted_questions_telegram}  
Solve it. Feel it.""",

        # Other Famous Books
        f"""⚔️ *{question_count} CHALLENGES STRIKE!*  
_*"The supreme art of war is to subdue the enemy without fighting." - Sun Tzu (The Art of War)*_  
Mind over might.  
- *Strategy:*  
{formatted_questions_telegram}  
Outthink. Win.""",

        f"""🌍 *{question_count} FOES DROP!*  
_*"It is not death that a man should fear, but never beginning to live." - Marcus Aurelius (Meditations)*_  
Live through this.  
- *Life:*  
{formatted_questions_telegram}  
Start now. Thrive.""",

        f"""🏜️ *{question_count} BATTLES CALL!*  
_*"I must not fear. Fear is the mind-killer." - Frank Herbert (Dune)*_  
Fear’s the enemy.  
- *Courage:*  
{formatted_questions_telegram}  
Kill it. Rise.""",

        f"""🧙 *{question_count} TESTS EMERGE!*  
_*"All we have to decide is what to do with the time that is given us." - Gandalf (The Fellowship of the Ring)*_  
Time’s yours.  
- *Moment:*  
{formatted_questions_telegram}  
Choose. Win.""",

        f"""🌲 *{question_count} CHALLENGES RISE!*  
_*"The only way out is through." - Robert Frost*_  
No retreat.  
- *Path:*  
{formatted_questions_telegram}  
Push. Prevail.""",

        # Mixed Inspirational
        f"""⭐ *{question_count} CHALLENGES LAND!*  
_*"Do or do not. There is no try." - Yoda (The Empire Strikes Back)*_  
Full send or bust.  
- *Force:*  
{formatted_questions_telegram}  
Do it. Master.""",

        f"""🗡️ *{question_count} FOES STRIKE!*  
_*"I am no man!" - Éowyn (The Return of the King)*_  
Defy everything.  
- *Defiance:*  
{formatted_questions_telegram}  
Shatter them. Win.""",

        f"""🔥 *{question_count} TRIALS DROP!*  
_*"Rage, rage against the dying of the light." - Dylan Thomas*_  
Burn fierce.  
- *Fire:*  
{formatted_questions_telegram}  
Rage on. Shine.""",

        f"""🪨 *{question_count} CHALLENGES IGNITE!*  
_*"The obstacle is the way." - Ryan Holiday (The Obstacle Is the Way)*_  
These are your steps.  
- *Road:*  
{formatted_questions_telegram}  
Climb. Conquer.""",

        f"""👹 *{question_count} BATTLES BEGIN!*  
_*"He who fights with monsters should look to it that he himself does not become a monster." - Nietzsche*_  
Stay sharp.  
- *Edge:*  
{formatted_questions_telegram}  
Slay. Survive.""",

        f"""🥊 *{question_count} TESTS ARRIVE!*  
_*"It’s only after we’ve lost everything that we’re free to do anything." - Chuck Palahniuk (Fight Club)*_  
Lose it all. Gain it back.  
- *Freedom:*  
{formatted_questions_telegram}  
Break free. Rule.""",

        f"""⚡ *{question_count} FOES CHALLENGE!*  
_*"Pain is inevitable. Suffering is optional." - Haruki Murakami*_  
Pain’s your ally.  
- *Strength:*  
{formatted_questions_telegram}  
Use it. Win.""",

        f"""🏛️ *{question_count} CHALLENGES DROP!*  
_*"Fortune favors the bold." - Virgil (The Aeneid)*_  
Boldness pays.  
- *Fortune:*  
{formatted_questions_telegram}  
Risk it. Take it.""",

        f"""⚔️ *{question_count} TRIALS RISE!*  
_*"What we do in life echoes in eternity." - Maximus (Gladiator)*_  
Make it echo.  
- *Echo:*  
{formatted_questions_telegram}  
Fight loud. Live forever.""",

        f"""🧠 *{question_count} BATTLES CALL!*  
_*"The mind is its own place, and in itself can make a heaven of hell." - John Milton (Paradise Lost)*_  
Hell’s theirs. Heaven’s yours.  
- *Mind:*  
{formatted_questions_telegram}  
Forge it. Win.""",

        f"""🔥 *{question_count} CHALLENGES STRIKE!*  
_*"If you’re going through hell, keep going." - Winston Churchill*_  
Hell’s the warmup.  
- *March:*  
{formatted_questions_telegram}  
Push on. Break through.""",

        f"""⚓ *{question_count} FOES DROP!*  
_*"I am the master of my fate, I am the captain of my soul." - William Ernest Henley (Invictus)*_  
You command.  
- *Destiny:*  
{formatted_questions_telegram}  
Steer it. Win it.""",

        f"""🏛️ *{question_count} TESTS IGNITE!*  
_*"A man’s worth is no greater than his ambitions." - Marcus Aurelius (Meditations)*_  
Aim high.  
- *Worth:*  
{formatted_questions_telegram}  
Reach it. Prove it.""",

        f"""🌍 *{question_count} CHALLENGES LAND!*  
_*"To live is to suffer; to survive is to find meaning in the suffering." - Viktor Frankl*_  
Meaning’s in the fight.  
- *Purpose:*  
{formatted_questions_telegram}  
Find it. Thrive.""",

        f"""⚡ *{question_count} BATTLES RISE!*  
_*"The best revenge is to be unlike him who performed the injury." - Marcus Aurelius (Meditations)*_  
Rise above.  
- *Revenge:*  
{formatted_questions_telegram}  
Be better. Win.""",

        f"""🌟 *{question_count} TRIALS DROP!*  
_*"You must be the change you wish to see in the world." - Mahatma Gandhi*_  
Change starts now.  
- *Change:*  
{formatted_questions_telegram}  
Be it. Make it.""",
    ]

    # Randomly select a template and send it
    selected_template = random.choice(notification_templates)
    telegram_msg = selected_template
    google_msg = selected_template.replace(formatted_questions_telegram, formatted_questions_google)

    send_telegram_message(telegram_msg)
    send_google_chat_message(google_msg)

    # Only update question_count if it has changed
    if question_count != last_count:
        set_db_value("question_count", question_count)
        set_db_value("last_update", datetime.datetime.now().strftime("%Y-%m-%d"))
        logging.info(f"Question count updated from {last_count} to {question_count}")
    else:
        logging.info("No change in question count, skipping update.")

def check_end_of_day():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)
    today = now.strftime("%Y-%m-%d")

    if now.hour >= 22 and (now.hour != 22 or now.minute >= 30):
        if get_db_value("last_update") != today and get_db_value("no_questions_sent") != today:
            telegram_eod = f"""🌌 *Cosmic Calm Report*  
_'The universe is under no obligation to make sense to you.' - Neil deGrasse Tyson_  
No new challenges today. Reality holds steady.  
☄️ Tomorrow’s wars await..."""

            google_eod = f"""🌌 *Cosmic Calm Report*  
_'The universe is under no obligation to make sense to you.' - Neil deGrasse Tyson_  
No new challenges today. Reality holds steady.  
☄️ Tomorrow’s wars await..."""
            send_telegram_message(telegram_eod)
            send_google_chat_message(google_eod)
            set_db_value("no_questions_sent", today)
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
