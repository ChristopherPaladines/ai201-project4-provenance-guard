import os
import json
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_llm_signal(text):
    prompt = f"""Analyze the following text and assess whether it was written by a human or an AI.

Respond ONLY with valid JSON in this exact format, no other text:
{{"score": <float between 0 and 1, where 1.0 means definitely AI-generated and 0.0 means definitely human-written>, "reason": "<short one-sentence explanation>"}}

Text to analyze:
\"\"\"{text}\"\"\"
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    raw_output = response.choices[0].message.content
    result = json.loads(raw_output)

    return result


if __name__ == "__main__":
    test_cases = {
        "human_casual": "ok so i finally tried that new ramen place downtown and honestly? underwhelming. the broth was fine but they put WAY too much sodium in it and i was thirsty for like three hours after.",
        "ai_generic": "Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits of AI are numerous, it is equally essential to consider the ethical implications.",
        "human_formal": "The relationship between monetary policy and asset price inflation has been extensively studied in the literature. Central banks face a fundamental tension between their mandate for price stability and unintended consequences.",
    }

    for label, text in test_cases.items():
        result = get_llm_signal(text)
        print(f"{label}: {result}")