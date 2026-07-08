import re

def get_stylometric_signal(text):
    # Split into sentences using . ! ? as boundaries
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]  # remove empty pieces

    # Count words in each sentence
    sentence_lengths = [len(s.split()) for s in sentences]

    # Calculate variance (average squared distance from the mean)
    mean_length = sum(sentence_lengths) / len(sentence_lengths)
    variance = sum((length - mean_length) ** 2 for length in sentence_lengths) / len(sentence_lengths)

    # Normalize variance into 0-1 (cap at 10, as planned)
    variance_score = 1 - min(variance / 10, 1)

    # Type-token ratio: unique words / total words
    words = text.lower().split()
    unique_words = set(words)
    ttr = len(unique_words) / len(words)

    # Invert TTR: high diversity = more human, so low AI-likeness
    ttr_score = 1 - ttr

    # Combine into one Signal 2 score
    signal2_score = (variance_score + ttr_score) / 2

    return {
        "score": round(signal2_score, 3),
        "sentence_variance": round(variance, 3),
        "type_token_ratio": round(ttr, 3)
    }


if __name__ == "__main__":
    test_cases = {
        "human_casual": "ok so i finally tried that new ramen place downtown and honestly? underwhelming. the broth was fine but they put WAY too much sodium in it and i was thirsty for like three hours after.",
        "ai_generic": "Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits of AI are numerous, it is equally essential to consider the ethical implications.",
        "human_formal": "The relationship between monetary policy and asset price inflation has been extensively studied in the literature. Central banks face a fundamental tension between their mandate for price stability and unintended consequences.",
    }

    for label, text in test_cases.items():
        result = get_stylometric_signal(text)
        print(f"{label}: {result}")