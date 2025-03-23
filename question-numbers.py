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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database Operations
def connect_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None  # Return None if connection fails

def setup_database():
    conn = connect_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""CREATE TABLE IF NOT EXISTS tracker 
                          (key TEXT PRIMARY KEY, value TEXT)""")
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
    """Format questions with platform-specific links"""
    base_url = f"{HR_BASE_URL}"
    formatted = []
    
    for name, slug in questions:
        if platform.lower() == "telegram":
            # Telegram Markdown format
            formatted.append(f"▫️ [{name}]({base_url}/{slug})")
        elif platform.lower() == "google_chat":
            # Google Chat link format
            formatted.append(f"▫️ <{base_url}/{slug}|{name}>")
    return "\n".join(formatted)

# Notification System
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        response = requests.post(url, data=data)
        if response.status_code != 200:
            logging.error(f"Telegram API error: Status code {response.status_code}, Response: {response.text}")
        else:
            logging.info("Telegram message sent successfully.")

    except requests.exceptions.RequestException as e:
        logging.error(f"Telegram Request Exception: {e}")

def send_google_chat_message(message):
    """Send message to Google Chat with proper formatting"""
    try:
        response = requests.post(
            GOOGLE_CHAT_WEBHOOK_URL,
            json={
                "text": message,
                "cards": [{
                    "sections": [{
                        "widgets": [{
                            "textParagraph": {
                                "text": message.replace("_", "*")  # Preserve emphasis
                            }
                        }]
                    }]
                }]
            }
        )
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

    last_count = int(get_db_value("question_count") or 0)

    if last_count == 0:
        # Replaced "First Blood!" with "🎉 Contest Launch!"
        telegram_initial = f"""🎉 *Contest Launch!* {question_count} challenges detected!
📌 **Initial Problems:**
{format_questions(questions, "telegram")}
_'First to solve gets bragging rights!' - Tony Stark_"""

        google_initial = f"""🎉 *Contest Launch!* {question_count} challenges detected!
📌 **Initial Problems:**
{format_questions(questions, "google_chat")}
_'First to solve gets bragging rights!' - Tony Stark_"""

        send_telegram_message(telegram_initial)
        send_google_chat_message(google_initial)
    else:
        difference = question_count - last_count
        if difference > 0:
            new_questions = questions[-difference:]
            templates = [
                (
                    f"🔥 *{difference} New Arena Challenge{'s' if difference > 1 else ''}!*\n"
                    "'Heroes are made by the paths they choose, not the powers they are graced with.' - Iron Man (Avengers)\n\n"
                    "🛡️ New Trials:\n{questions}\n\n"
                    "_Suit up, Shellhead! 🦾_"
                ),
                (
                    f"⚡ *{difference} Shockwave Alert!*\n"
                    "'That's what heroes do.' - Thor (Avengers: Endgame)\n\n"
                    "🌌 New Battles:\n{questions}\n\n"
                    "_Stormbreaker ready! ⚡_"
                ),
                (
                    f"🦇 *{difference} Gotham Emergency!*\n"
                    "'Why do we fall? So we can learn to pick ourselves up.' - Alfred (Batman Begins)\n\n"
                    "🚨 New Missions:\n{questions}\n\n"
                    "_I am the night! 🌑_"
                ),
                (
                    f"🌠 *{difference} Cosmic Threat{'s' if difference > 1 else ''} Detected!*\n"
                    "'Dread it. Run from it. Destiny arrives all the same.' - Thanos (Infinity War)\n\n"
                    "🪐 New Conflicts:\n{questions}\n\n"
                    "_Perfectly balanced... ⚖️_"
                ),
                (
                    f"🧠 *{difference} Mind Palace Challenge{'s' if difference > 1 else ''}!*\n"
                    "'You see, but you do not observe.' - Sherlock Holmes (A Study in Scarlet)\n\n"
                    "🔍 New Puzzles:\n{questions}\n\n"
                    "_The game is afoot! 🕵️_"
                ),
                (
                    f"⚔️ *{difference} New Battlefield{'s' if difference > 1 else ''}!*\n"
                    "'Speak less than you know; have more than you show.' - (48 Laws of Power, Law 4)\n\n"
                    "🛡️ Challenges:\n{questions}\n\n"
                    "_Power is my currency. 💰_"
                ),
                (
                    f"💥 *{difference} Boom! New Problem{'s' if difference > 1 else ''}!*\n"
                    "'Problems are only solutions in work clothes.' - (The Subtle Art of Not Giving a F*ck)\n\n"
                    "🧨 Challenges:\n{questions}\n\n"
                    "_Embrace the suck. 💣_"
                ),
                (
                    f"🕷️ *{difference} Web-Slinging Challenge{'s' if difference > 1 else ''}!*\n"
                    "'With great power comes great responsibility.' - Uncle Ben (Spider-Man)\n\n"
                    "🕸️ New Tests:\n{questions}\n\n"
                    "_Your move, Tiger! 🐯_"
                ),
                (
                    f"🧪 *{difference} Experiment{'s' if difference > 1 else ''} Ready!*\n"
                    "'The true sign of intelligence is not knowledge but imagination.' - Einstein (Atomic Habits)\n\n"
                    "⚗️ New Labs:\n{questions}\n\n"
                    "_Genius at work! 🧬_"
                ),
                (
                    f"🦉 *{difference} Wisdom Check{'s' if difference > 1 else ''}!*\n"
                    "'The key to immortality is living a life worth remembering.' - Bruce Lee (Tao of Jeet Kune Do)\n\n"
                    "📜 New Lessons:\n{questions}\n\n"
                    "_Be water, my friend. 💧_"
                ),
                (
                    f"🌪️ *{difference} Storm Warning{'s' if difference > 1 else ''}!*\n"
                    "'Chaos isn't a pit. Chaos is a ladder.' - Littlefinger (Game of Thrones)\n\n"
                    "🌀 New Trials:\n{questions}\n\n"
                    "_Climb or fall. 🪜_"
                ),
                (
                    f"🎭 *{difference} New Act{'s' if difference > 1 else ''}!*\n"
                    "'All the world's a stage, and all the men and women merely players.' - Shakespeare (As You Like It)\n\n"
                    "🎪 Performances:\n{questions}\n\n"
                    "_Break a leg! 🦵_"
                ),
                (
                    f"🔮 *{difference} Prophecy Update!*\n"
                    "'It does not do to dwell on dreams and forget to live.' - Dumbledore (Harry Potter)\n\n"
                    "🧙♂️ New Seers:\n{questions}\n\n"
                    "_Mischief managed! 🌕_"
                ),
                (
                    f"🧭 *{difference} Navigation Test{'s' if difference > 1 else ''}!*\n"
                    "'Not all those who wander are lost.' - Tolkien (Lord of the Rings)\n\n"
                    "🗺️ New Paths:\n{questions}\n\n"
                    "_Adventure awaits! 🏔️_"
                ),
                (
                    f"🛡️ *{difference} Spartan Challenge{'s' if difference > 1 else ''}!*\n"
                    "'This. Is. SPARTA!' - Leonidas (300)\n\n"
                    "⚔️ New Battles:\n{questions}\n\n"
                    "_Tonight we dine in hell! 🔥_"
                ),
                (
                    f"🎲 *{difference} High-Risk Game{'s' if difference > 1 else ''}!*\n"
                    "'You mustn't be afraid to dream a little bigger.' - Eames (Inception)\n\n"
                    "🃏 New Layers:\n{questions}\n\n"
                    "_Your mind is the scene. 🧠_"
                ),
                (
                    f"🌑 *{difference} Dark Side Challenge{'s' if difference > 1 else ''}!*\n"
                    "'Do. Or do not. There is no try.' - Yoda (Star Wars)\n\n"
                    "⚫ New Trials:\n{questions}\n\n"
                    "_May the Force be with you. ✨_"
                ),
                (
                    f"🧲 *{difference} Magnetic Problem{'s' if difference > 1 else ''}!*\n"
                    "'The most powerful magnet in the universe is focus.' - (The 5 AM Club)\n\n"
                    "⚡ New Attractions:\n{questions}\n\n"
                    "_Polarize your mind! 🧲_"
                ),
                (
                    f"🪓 *{difference} Lumberjack Challenge{'s' if difference > 1 else ''}!*\n"
                    "'When you're good at something, never do it for free.' - Joker (The Dark Knight)\n\n"
                    "🪵 New Logs:\n{questions}\n\n"
                    "_Why so serious? 😈_"
                ),
                (
                    f"🦾 *{difference} Cybernetic Threat{'s' if difference > 1 else ''}!*\n"
                    "'I'll be back.' - Terminator (The Terminator)\n\n"
                    "🤖 New Targets:\n{questions}\n\n"
                    "_Judgment day arrived! ☢️_"
                ),
                (
                    f"🧨 *{difference} Explosive Situation{'s' if difference > 1 else ''}!*\n"
                    "'Let me put a smile on that face.' - Joker (The Dark Knight)\n\n"
                    "💣 New Triggers:\n{questions}\n\n"
                    "_Madness is the emergency exit. 🚪_"
                ),
                (
                    f"🪐 *{difference} Interstellar Challenge{'s' if difference > 1 else ''}!*\n"
                    "'We are all made of stars.' - (Cosmos, Carl Sagan)\n\n"
                    "🌠 New Frontiers:\n{questions}\n\n"
                    "_To infinity and beyond! 🚀_"
                ),
                (
                    f"🧬 *{difference} Genetic Test{'s' if difference > 1 else ''}!*\n"
                    "'Life finds a way.' - Ian Malcolm (Jurassic Park)\n\n"
                    "🦖 New Experiments:\n{questions}\n\n"
                    "_Hold onto your butts! 🍑_"
                ),
                (
                    f"🕵️ *{difference} Covert Op{'s' if difference > 1 else ''}!*\n"
                    "'The name's Bond. James Bond.' - (Casino Royale)\n\n"
                    "🔫 New Missions:\n{questions}\n\n"
                    "_Shaken, not stirred. 🍸_"
                ),
                (
                    f"🧿 *{difference} Third Eye Challenge{'s' if difference > 1 else ''}!*\n"
                    "'Reality is often disappointing.' - Thanos (Infinity War)\n\n"
                    "🌀 New Illusions:\n{questions}\n\n"
                    "_Perfectly balanced. ⚖️_"
                ),
                (
                    f"🗡️ *{difference} Assassin's Trial{'s' if difference > 1 else ''}!*\n"
                    "'Nothing is true, everything is permitted.' - (Assassin's Creed)\n\n"
                    "🏹 New Contracts:\n{questions}\n\n"
                    "_Requiescat in pace. ☠️_"
                ),
                (
                    f"🧪 *{difference} Formula Update!*\n"
                    "'Great Scott!' - Doc Brown (Back to the Future)\n\n"
                    "⏳ New Paradoxes:\n{questions}\n\n"
                    "_1.21 gigawatts! ⚡_"
                ),
                (
                    f"🦹 *{difference} Villainous Scheme{'s' if difference > 1 else ''}!*\n"
                    "'Do you feel in charge?' - Bane (The Dark Knight Rises)\n\n"
                    "💀 New Threats:\n{questions}\n\n"
                    "_The fire rises! 🔥_"
                ),
                (
                    f"🧙♂️ *{difference} Wizard's Duel{'s' if difference > 1 else ''}!*\n"
                    "'You shall not pass!' - Gandalf (Lord of the Rings)\n\n"
                    "⚡ New Spells:\n{questions}\n\n"
                    "_Fly, you fools! 🧙_"
                ),
                (
                    f"🦸♂️ *{difference} Kryptonian Test{'s' if difference > 1 else ''}!*\n"
                    "'Truth, justice, and a better tomorrow.' - Superman (DC Comics)\n\n"
                    "🦸♀️ New Trials:\n{questions}\n\n"
                    "_Up, up, and away! 🚀_"
                )
            ]

            chosen = random.choice(templates)
            suffix = "s" if difference > 1 else ""
            # Create platform-specific messages
            telegram_msg = chosen.format(
                difference=difference,
                suffix=suffix,
                questions=format_questions(new_questions, platform="telegram")
            )

            google_msg = chosen.format(
                difference=difference,
                suffix=suffix,
                questions=format_questions(new_questions, platform="google_chat")
            )

            send_telegram_message(telegram_msg)
            send_google_chat_message(google_msg)

    set_db_value("question_count", question_count)
    set_db_value("last_update", datetime.datetime.now().strftime("%Y-%m-%d"))


def check_end_of_day():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)
    today = now.strftime("%Y-%m-%d")

    if now.hour >= 22 and (now.hour != 22 or now.minute >= 30):
        if get_db_value("last_update") != today and get_db_value("no_questions_sent") != today:
            templates = [
                (
                    "🌌 *Cosmic Calm Report*\n"
                    "'The universe is under no obligation to make sense to you.' - Neil deGrasse Tyson (Astrophysics for People in a Hurry)\n\n"
                    "_No new challenges today. Reality remains intact._\n\n"
                    "☄️ Tomorrow's battles await..."
                ),
                (
                    "🦇 *Gotham Night Report*\n"
                    "'The night is always darkest before the dawn.' - Harvey Dent (The Dark Knight)\n\n"
                    "_No new problems. City sleeps peacefully._\n\n"
                    "🕶️ Vigilance continues..."
                ),
                (
                    "🧪 *Lab Closure Notice*\n"
                    "'Negative results are just what I want.' - Tony Stark (Iron Man)\n\n"
                    "_No experiments today. Jarvis is recalibrating._\n\n"
                    "🔬 Innovation resumes tomorrow."
                ),
                (
                    "🛡️ *Asgardian Update*\n"
                    "'There will never be a smarter HackerRank bot.' - Loki (Avengers)\n\n"
                    "_No new trials. Realm remains protected._\n\n"
                    "⚡ Thor's hammer idle..."
                ),
                (
                    "🕵️ *Moriarty's Report*\n"
                    "'You see, but you do not observe.' - Sherlock Holmes (A Scandal in Bohemia)\n\n"
                    "_No new puzzles. Criminal mastermind at rest._\n\n"
                    "🔍 Deduction paused..."
                ),
                (
                    "🧿 *Mystic Update*\n"
                    "'Dormammu, I've come to bargain!' - Dr. Strange (Doctor Strange)\n\n"
                    "_No new challenges. Time loop intact._\n\n"
                    "🌀 Reality holds..."
                ),
                (
                    "🦉 *Hogwarts Bulletin*\n"
                    "'Happiness can be found even in the darkest of times.' - Dumbledore (Harry Potter)\n\n"
                    "_No new spells. Chamber of secrets remains closed._\n\n"
                    "⚡ Patronus charged..."
                ),
                (
                    "🌑 *Sith Council Update*\n"
                    "'The dark side clouds everything.' - Yoda (Star Wars)\n\n"
                    "_No new conflicts. Balance maintained._\n\n"
                    "⚔️ Peace prevails..."
                ),
                (
                    "🧭 *Explorer's Log*\n"
                    "'It's not the destination that matters, but the journey.' - The Alchemist (Paulo Coelho)\n\n"
                    "_No new paths. Compass still._\n\n"
                    "🗺️ New routes tomorrow..."
                ),
                (
                    "⚗️ *Wakanda Report*\n"
                    "'In times of crisis, the wise build bridges.' - T'Challa (Black Panther)\n\n"
                    "_No new threats. Vibranium secure._\n\n"
                    "🛡️ Wakanda forever..."
                ),
                (
                    "🕸️ *Daily Bugle Update*\n"
                    "'You mess with Spidey, you get the horns!' - J. Jonah Jameson\n\n"
                    "_No new villains. Photos on standby._\n\n"
                    "📸 Parker, where are my pictures?!"
                ),
                (
                    "🧨 *Goblin's Note*\n"
                    "'You know, I'm something of a coder myself.' - Norman Osborn (Spider-Man)\n\n"
                    "_No new gliders. Pumpkin bombs inactive._\n\n"
                    "🎃 Stay vigilant..."
                ),
                (
                    "🦾 *Cybernetic Report*\n"
                    "'I am Groot.' - Groot (Guardians of the Galaxy)\n\n"
                    "_No new branches. Flora colossus dormant._\n\n"
                    "🌳 I am Steve Rogers..."
                ),
                (
                    "🧲 *X-Mansion Update*\n"
                    "'Mutant and proud.' - Magneto (X-Men)\n\n"
                    "_No new tests. Cerebro offline._\n\n"
                    "🧠 Xavier's dream continues..."
                ),
                (
                    "🪐 *Stark Industries Memo*\n"
                    "'Sometimes you gotta run before you can walk.' - Tony Stark (Iron Man)\n\n"
                    "_No new tech. Arc reactor stable._\n\n"
                    "⚡ Repulsors charging..."
                ),
                (
                    f"⚔️ *Valhalla Report*\n"
                    "'The sun will shine on us again.' - Loki (Thor: Ragnarok)\n\n"
                    "_No new wars. Bifrost quiet._\n\n"
                    "🌈 Heimdall watches..."
                ),
                (
                    "🕯️ *Bat-Signal Update*\n"
                    "'It's not who I am underneath, but what I do that defines me.' - Batman (Batman Begins)\n\n"
                    "_No new crimes. Gotham sleeps._\n\n"
                    "🦇 Justice rests..."
                ),
                (
                    "🧬 *Jurassic Park Alert*\n"
                    "'Life breaks free. Life finds a way.' - Ian Malcolm (Jurassic Park)\n\n"
                    "_No new dinosaurs. Electrified fences active._\n\n"
                    "🦖 Hold onto your butts..."
                ),
                (
                    "🛸 *Area 51 Update*\n"
                    "'I want to believe.' - Fox Mulder (The X-Files)\n\n"
                    "_No new UFOs. Truth still out there._\n\n"
                    "👽 Trust no one..."
                ),
                (
                    "🎭 *Theatre Closure Notice*\n"
                    "'All the world's indeed a stage.' - William Shakespeare\n\n"
                    "_No new acts. Curtains drawn._\n\n"
                    "🎪 Encore tomorrow..."
                ),
                (
                    "🧨 *Joker's Diary Entry*\n"
                    "'Madness is the emergency exit.' - (The Killing Joke)\n\n"
                    "_No new pranks. Chemical plant quiet._\n\n"
                    "🤡 Why so serious?..."
                ),
                (
                    "🪓 *Winterfell Report*\n"
                    "'Winter is coming.' - House Stark (Game of Thrones)\n\n"
                    "_No new wars. White Walkers dormant._\n\n"
                    "❄️ The North remembers..."
                ),
                (
                    "🦄 *Mythical Update*\n"
                    "'The flame that burns twice as bright burns half as long.' - (Blade Runner)\n\n"
                    "_No new legends. Unicorns grazing._\n\n"
                    "🌈 Magic recharges..."
                ),
                (
                    "🧭 *Pirate's Log*\n"
                    "'Not all treasure is silver and gold.' - Jack Sparrow (Pirates of the Caribbean)\n\n"
                    "_No new islands. Rum stocks full._\n\n"
                    "🏴‍☠️ Savvy?..."
                ),
                (
                    "🌪️ *Oz Report*\n"
                    "'There's no place like home.' - Dorothy (The Wizard of Oz)\n\n"
                    "_No new tornados. Ruby slippers secure._\n\n"
                    "👠 Follow the yellow brick road..."
                ),
                (
                    "🛡️ *Spartan Bulletin*\n"
                    "'Spartans never retreat! Spartans never surrender!' - King Leonidas (300)\n\n"
                    "_No new invasions. Hot gates calm._\n\n"
                    "⚔️ Tonight we dine..."
                ),
                (
                    "🧿 *Oracle's Vision*\n"
                    "'Know thyself.' - Temple of Apollo at Delphi\n\n"
                    "_No new prophecies. Pythia meditates._\n\n"
                    "🌀 The future waits..."
                ),
                (
                    "⚡ *Daily Prophet Update*\n"
                    "'Turn to page 394.' - Severus Snape (Harry Potter)\n\n"
                    "_No new dark marks. Ministry vigilant._\n\n"
                    "🧙♂️ Mischief managed..."
                ),
                (
                    "🪐 *Guardians' Memo*\n"
                    "'We're the Guardians of the Galaxy, bitch!' - Rocket Raccoon\n\n"
                    "_No new galaxies. Milano docked._\n\n"
                    "🚀 Star-Lord signing off..."
                )
            ]

            message = random.choice(templates)
            send_telegram_message(message)
            send_google_chat_message(message)
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
