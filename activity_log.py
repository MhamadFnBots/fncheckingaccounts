import json
from datetime import datetime

def log_activity(user_id: int, account_id: str, action: str):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "telegram_user_id": user_id,
        "account_id": account_id,  # Mask or hash this if necessary
        "action": action
    }

    with open("activity_log.json", "a") as log_file:
        log_file.write(json.dumps(log_entry) + "\n")