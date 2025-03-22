import requests
import os
import datetime
import random
import pytz  # Import the pytz library

# Replace with your Telegram bot API token and chat ID
TELEGRAM_BOT_TOKEN = "7211810846:AAFchPh2P70ZWlQPEH1WAVgaLxngvkHmz3A"
TELEGRAM_CHAT_ID = "1631288026"

# Replace with your Google Chat webhook URL
GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAAABLlXXMM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=AxaA5jffPFX7ks0JXC4tGUkisYoSRvH8rv0BtX9xHBg"  # VERY IMPORTANT!

# File to store the last question count and last update time
COUNT_FILE = "question_count.txt"
LAST_UPDATE_FILE = "last_update.txt"
NO_QUESTIONS_SENT_FILE = "no_questions_sent.txt"  # New file to track "no questions" message

# Replace the cookies below with your extracted cookies
COOKIES = {
    "hackerrank_mixpanel_token": "2dab64b2-51e9-4c69-a1da-0014edcf9825",
    "peacemakers24b1_crp": "*nil*",
    "session_id": "0yhigm53-1740482754625",
    "user_type": "hacker",
    "_hrank_session": "ebfd03a3d3d948fd372abfe176cbb7f2",
}

# Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

# Contest Slug (Change if needed)
CONTEST_SLUG = "peacemakers24b1"

def fetch_questions():
    """Fetch all questions from the contest and return their names."""
    offset = 0
    limit = 10
    all_questions = []

    while True:
        url = f"https://www.hackerrank.com/rest/contests/{CONTEST_SLUG}/challenges?offset={offset}&limit={limit}&track_login=true"

        response = requests.get(url, headers=HEADERS, cookies=COOKIES)

        if response.status_code == 200:
            data = response.json()
            questions = data.get("models", [])

            if not questions:  # No more questions left
                break

            for question in questions:
                all_questions.append(question["name"])  # Store question names

            offset += limit  # Move to the next batch

        else:
            print(f"❌ Request Failed! Status Code: {response.status_code}")
            return None, []  # Return None for count and an empty list

    return len(all_questions), all_questions  # Return both count and names

def send_telegram_message(message):
    """Send a Telegram message notification."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"  # Enable Markdown formatting
    }
    response = requests.post(url, data=data)

    if response.status_code == 200:
        print("✅ Telegram notification sent!")
    else:
        print(f"❌ Failed to send Telegram notification. Status code: {response.status_code}, Response: {response.text}") # Enhanced error message

def send_google_chat_message(message):
    """Send a message to Google Chat using a webhook."""
    url = GOOGLE_CHAT_WEBHOOK_URL
    data = {
        "text": message
    }
    response = requests.post(url, json=data)

    if response.status_code == 200:
        print("✅ Google Chat notification sent!")
    else:
        print(f"❌ Failed to send Google Chat notification. Status code: {response.status_code}, Response: {response.text}")

def get_last_count():
    """Read the last stored question count from the file."""
    if os.path.exists(COUNT_FILE):
        with open(COUNT_FILE, "r") as file:
            try:
                return int(file.read().strip())
            except ValueError:
                return None  # Handle corrupt or empty file
    return None  # Return None if file doesn't exist

def save_new_count(count):
    """Save the latest question count to the file."""
    with open(COUNT_FILE, "w") as file:
        file.write(str(count))

    # Save last update time
    with open(LAST_UPDATE_FILE, "w") as file:
        file.write(datetime.datetime.now().strftime("%Y-%m-%d"))

def get_last_update_date():
    """Read the last update date from file."""
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, "r") as file:
            return file.read().strip()
    return None

def did_send_no_questions_message_today():
    """Check if the "no questions today" message was already sent today."""
    if os.path.exists(NO_QUESTIONS_SENT_FILE):
        with open(NO_QUESTIONS_SENT_FILE, "r") as file:
            last_sent_date = file.read().strip()
            return last_sent_date == datetime.datetime.now().strftime("%Y-%m-%d")
    return False

def mark_no_questions_message_sent():
    """Mark that the "no questions today" message was sent today."""
    with open(NO_QUESTIONS_SENT_FILE, "w") as file:
        file.write(datetime.datetime.now().strftime("%Y-%m-%d"))

def notify_question_count():
    """Fetch, compare, and send question count update with names to both Telegram and Google Chat."""
    question_count, question_names = fetch_questions()

    if question_count is None:
        print("❌ Failed to fetch questions.")
        return

    last_count = get_last_count()

    if last_count is None:
        message = f"🚀 First Check! {question_count} questions are live!\n\n📌 **Latest Questions:**\n" + "\n".join([f"🔹 {q}" for q in question_names])
    else:
        difference = question_count - last_count
        if difference > 0:
            new_questions = question_names[-difference:]  # Get only newly added questions

            messages = [
                f"🔥 {difference} new coding challenge just arrived! Will you be the first to solve them? ⚡",
                f"💡 {difference} fresh problem are waiting for you. Time to showcase your skills! 🚀",
                f"⚔️ A new war begins! {difference} more puzzle to crack. Are you the coding champion? 👑",
                f"🤖 {difference} fresh problem have dropped! Will you rise or fall? The battle is on! 🔥",
                f"⏳ Time waits for none! {difference} new question are here. Ready to claim your rank? 🏆",
                f"🚀 A new era begins... {difference} fresh challenge have arrived. Will you rise to the occasion? ⚔️🔥",
                f"🧠 The battle of minds ignites! {difference} new problem await. Who will claim victory? 🏆",
                f"⚡ Anomaly detected! {difference} new coding puzzle have surfaced. Time to decode the unknown! 🤖",
                f"🌌 The void shifts... {difference} challenge have emerged. Only the worthy will conquer them! ⚔️",
                f"🛡️ A warrior’s path is never easy! {difference} new trials have been unleashed. Face them with courage! 💡",
                f"⏳ Time waits for no one! {difference} more problem stand between you and greatness. Will you take them on? 🏅",
                f"📜 A new scroll has been uncovered! The secrets within these {difference} question are waiting for a true solver! 🔍",
                f"💥 The battlefield roars! {difference} new coding quest have arrived. Show the world your skills! 🌟",
                f"new challenges... {difference} coding mystery await. Will you solve them before anyone else? ⚙️",
                f"🕵️ A secret has been unveiled... {difference} fresh problem are here. The hunt for solutions begins now! 🔥"
            ]

            random_index = random.randint(0, len(messages) - 1)
            base_message = messages[random_index]

            question_list = "\n".join([f"✨ {q}" for q in new_questions])
            message = f"{base_message}\n\n📌 New Questions:\n{question_list}"

            send_telegram_message(message)
            send_google_chat_message(message)
                
            
        else:
            print("No new questions. Skipping notification.")
            return

    save_new_count(question_count)

def check_end_of_day():
    """Send a message if no new questions were uploaded by 2:30 PM IST, only once per day."""
    #utc_now = datetime.datetime.utcnow()

    # It's telling you that utcnow is deprecated. use datetime.datetime.now(datetime.timezone.utc) instead
    utc_now = datetime.datetime.now(datetime.timezone.utc)

    ist_timezone = pytz.timezone("Asia/Kolkata")  # Or "Asia/Calcutta"
    ist_time = utc_now.astimezone(ist_timezone)

    print(f"Current time (UTC): {utc_now}")
    print(f"Current time (IST): {ist_time}")

    if (ist_time.hour > 22 or (ist_time.hour == 22 and ist_time.minute >= 30)) and not did_send_no_questions_message_today():


        last_update_date = get_last_update_date()
        today_date = ist_time.strftime("%Y-%m-%d")

        print(f"Last update date: {last_update_date}")
        print(f"Today's date: {today_date}")
        print(f"Did send no questions message today?: {did_send_no_questions_message_today()}")

        if last_update_date != today_date and not did_send_no_questions_message_today():  # No update today AND message not already sent
            messages = [
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
"⚡ The leaderboard will remember your name... but only if yougrind in the days no one sees.",
"💪 A silent day is the best day... because that's when only the real ones keep coding.",
"📜 One empty day will never break a legend... but one skipped day might.",
"🔥 No new questions... But there's always one unsolved problem — the one inside your own mind.",
"⚔️ The journey is not about coding every day... it's about becoming the kind of person who codes every day."
            ]
            random_index = random.randint(0, len(messages) - 1)
            message = messages[random_index]

            send_telegram_message(message)
            send_google_chat_message(message) # Send to Google Chat as well
            mark_no_questions_message_sent()  # Mark message as sent
        else:
            print("Conditions not met for 'no questions today' message.")
    else:
        print("Time is not yet 10:30 PM IST.")

# Run the function
notify_question_count()
check_end_of_day()
