import json
import os
from datetime import datetime, timezone

LOG_FILE = "audit_log.json"

def load_log():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        return json.load(f)

def save_log(entries):
    with open(LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)

def add_log_entry(entry):
    entries = load_log()
    entries.append(entry)
    save_log(entries)

def get_log_entries():
    return load_log()


def update_status_and_add_appeal(content_id, creator_reasoning):
    entries = load_log()
    for entry in entries:
        if entry["content_id"] == content_id:
            entry["status"] = "under_review"
            entry["appeal_reasoning"] = creator_reasoning
            save_log(entries)
            return entry
    return None