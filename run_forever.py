import time
import pytz
from datetime import datetime
from subprocess import run

# Set the timezone (Adjust if needed)
IST = pytz.timezone("Asia/Kolkata")

while True:
    # Get current time in IST
    now = datetime.now(IST)
    current_hour = now.hour

    # Run only between 2 PM (14) and 11 PM (23) IST
    if 14 <= current_hour <= 23:
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Running script...")
        
        # Run the main script (replace with your actual script)
        run(["python", "question-numbers.py"])
        
        # Wait for 1 minute before the next execution
        time.sleep(60)
    else:
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Outside working hours, sleeping...")
        time.sleep(600)  # Sleep for 10 minutes outside working hours
