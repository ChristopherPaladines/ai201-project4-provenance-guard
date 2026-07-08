from flask import Flask, jsonify, request
from signals import get_llm_signal
from stylometry import get_stylometric_signal
import uuid
from audit_log import add_log_entry, get_log_entries
from datetime import datetime, timezone
from audit_log import add_log_entry, get_log_entries, update_status_and_add_appeal
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

def get_label(score):
    if score <= 0.40:
        return "This text is highly likely to be written by a human."
    elif score <= 0.74:
        return "This text shares traits with both human and AI writing, so the system is uncertain about its origin."
    else:
        return "This text shows a high presence of AI-generated patterns."


@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json()
    text = data.get("text")
    creator_id = data.get("creator_id")

    signal1_result = get_llm_signal(text)
    signal2_result = get_stylometric_signal(text)

    combined_score = (0.5 * signal1_result["score"]) + (0.5 * signal2_result["score"])
    label = get_label(combined_score)

    content_id = str(uuid.uuid4())

    response = {
        "content_id": content_id,
        "creator_id": creator_id,
        "signal1_score": signal1_result["score"],
        "signal2_score": signal2_result["score"],
        "confidence": round(combined_score, 3),
        "label": label
    }

    # Only include the LLM's reason if uncertain or likely AI
    if combined_score > 0.40:
        response["reason"] = signal1_result["reason"]

    log_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signal1_score": signal1_result["score"],
        "signal2_score": signal2_result["score"],
        "confidence": round(combined_score, 3),
        "label": label,
        "status": "classified"
    }
    add_log_entry(log_entry)

    return jsonify(response)

@app.route("/log", methods=["GET"])
def log():
    return jsonify({"entries": get_log_entries()})



@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json()
    content_id = data.get("content_id")
    creator_reasoning = data.get("creator_reasoning")

    updated_entry = update_status_and_add_appeal(content_id, creator_reasoning)

    if updated_entry is None:
        return jsonify({"error": "content_id not found"}), 404

    return jsonify({
        "message": "Appeal received",
        "content_id": content_id,
        "status": updated_entry["status"]
    })

if __name__ == "__main__":
    app.run(debug=True, port=5050)

