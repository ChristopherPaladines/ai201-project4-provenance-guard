# ai201-project4-provenance-guard

# Provenance Guard

A backend system that classifies creative writing as human- or AI-generated, using a 0–1 confidence 
score, transparency labels, and an appeals workflow.

## Architecture Overview

A submission enters through `POST /submit`, where the raw text is sent to two independent detection 
signals: an LLM-based semantic check (Groq) and a stylometric/structural check (sentence length 
variance + vocabulary diversity). Each signal returns a score between 0 and 1. These two scores are 
combined with equal (50/50) weighting into a single confidence score, which is then mapped to one of 
three transparency labels based on defined thresholds. Every submission — content ID, both signal 
scores, the combined score, and the resulting label — is written to a structured audit log, and the 
full response (including the label text) is returned to the user.

Appeals follow a simpler path: `POST /appeal` takes a content ID and the creator's reasoning, updates 
that content's status to "under_review" without recalculating the original score, and logs the appeal 
reasoning alongside the original decision so both are visible together.

SUBMISSION FLOW
[User] --text--> POST /submit --> Signal 1 (Groq LLM) --score+reason-->
--> Signal 2 (Stylometrics) --score-->
--> Confidence Scoring (50/50 avg) -->
--> Transparency Label --> Audit Log --> [User] (JSON response)
APPEAL FLOW
[User] --content_id + reasoning--> POST /appeal --> Update Status ("under_review")
--> Audit Log (linked to original) --> [User] (confirmation)

## Detection Signals

**Signal 1 — LLM-based classification (Groq, llama-3.3-70b-versatile)**
Measures semantic and stylistic coherence — whether the text *reads* as human- or AI-written, judged 
holistically by the model. Output is a JSON object with a `score` (float 0–1, closer to 1 = more 
AI-like) and a `reason` (short natural-language explanation). This signal was chosen because it can 
catch tone, fluency, and phrasing patterns that a purely statistical approach would miss entirely.
*What it misses:* it's a black box — we can't inspect why it arrived at a given score beyond the 
returned `reason` text. If a human's natural writing style resembles common AI phrasing habits (e.g., 
frequent formal transitions), it may be scored as AI-like with no way to verify or override the 
internal reasoning.

**Signal 2 — Stylometric heuristics (pure Python)**
Measures sentence length variance and type-token ratio (vocabulary diversity). AI-generated text tends 
to have more uniform sentence lengths and repeat vocabulary more; human writing tends to vary more in 
both. Each raw metric is normalized to 0–1 and averaged into a single score. This signal was chosen 
because it's mathematically measurable and independent of any model's judgment — it checks structure, 
not "feel."
*What it misses:* on short text samples, variance and vocabulary ratio are statistically unstable — a 
single well-written but short paragraph can produce a misleading score in either direction. We observed 
this directly in testing (see below). Genre-appropriate uniform writing (technical or legal writing, 
for instance) can also trip this signal into a false "AI-like" reading, since intentional repetition 
for clarity looks identical to algorithmic uniformity.

**Why these two signals together:** they are genuinely independent — one is semantic/holistic (LLM), 
the other is structural/statistical (stylometric) — so they catch different classes of AI-writing 
patterns rather than two versions of the same approach.

## Confidence Scoring

Both signals output a float between 0 and 1. They are combined with equal weighting:

combined_score = (0.5 * signal1_score) + (0.5 * signal2_score)
Equal weighting was chosen because, without a labeled dataset to validate against, there's no principled 
basis yet for trusting one signal over the other — 50/50 is the most defensible default.

Thresholds:
- 0.00 – 0.40 → likely human
- 0.41 – 0.74 → uncertain
- 0.75 – 1.00 → likely AI

The "likely AI" threshold is set deliberately high (0.75, not just above the midpoint) because a false 
positive — labeling a human's work as AI-generated — is worse than a false negative on a creative 
writing platform. The wider "uncertain" band keeps the system cautious rather than confidently 
mislabeling borderline cases.

**Two real test examples from this system:**

*High-confidence human example* — submitted casual, first-person restaurant review text:
```json
{
  "confidence": 0.1,
  "signal1_score": 0.2,
  "signal2_score": 0.0,
  "label": "This text is highly likely to be written by a human."
}
```

*Uncertain example* — submitted a short, generic AI-style sentence about artificial intelligence:
```json
{
  "confidence": 0.65,
  "signal1_score": 0.8,
  "signal2_score": 0.5,
  "label": "This text shares traits with both human and AI writing, so the system is uncertain about its origin.",
  "reason": "The text's formal tone and generic statement suggest AI generation, but its simplicity and lack of distinct AI hallmarks leave some uncertainty."
}
```

**Validation:** we tested the stylometric signal independently against three sample texts (clearly 
casual/human, clearly generic/AI, and formal/human) before combining it with Signal 1. Signal 2 alone 
misfired on the AI-generic sample in one test — its sentence-length variance was actually *higher* than 
the formal-human sample's, which would have (incorrectly) scored it as more human. This confirmed why 
combining with Signal 1 matters: no single signal is reliable in isolation. This is a documented, known 
limitation of stylometric approaches on short text, similar to struggles seen in commercial tools like 
Grammarly and Turnitin's AI detection features on short inputs.

## Transparency Label

All three labels share a consistent wrapper: **"Analyzation complete: The system has reviewed the text."**

| Confidence Range | Label Text |
|---|---|
| 0.00 – 0.40 (high-confidence human) | "This text is highly likely to be written by a human." |
| 0.41 – 0.74 (uncertain) | "This text shares traits with both human and AI writing, so the system is uncertain about its origin." |
| 0.75 – 1.00 (high-confidence AI) | "This text shows a high presence of AI-generated patterns." |

The Groq LLM's `reason` text is included in the response only when the label is "uncertain" or "likely 
AI" — for high-confidence human results, it's omitted since it adds no value there. It is always saved 
to the audit log regardless of label.

## Appeals Workflow

Only content labeled "uncertain" or "likely AI" can be appealed; "likely human" results have no 
meaningful reason to be contested. A creator submits a `content_id` and `creator_reasoning` to 
`POST /appeal`. The system does not recalculate the original score or label (automated 
re-classification is not required) — it updates the content's `status` field to `"under_review"` and 
logs the appeal reasoning alongside the original decision in the same audit log entry, so a reviewer 
sees both together.

**Tested example:**
```json
// Request
{"content_id": "30679ec6-5114-4489-a570-33963cbfa435", "creator_reasoning": "I wrote this myself based on personal experience."}

// Response
{"content_id": "30679ec6-5114-4489-a570-33963cbfa435", "message": "Appeal received", "status": "under_review"}
```

Confirmed via `GET /log` that the entry updated correctly:
```json
{
  "appeal_reasoning": "I wrote this myself based on personal experience.",
  "status": "under_review",
  "confidence": 0.65,
  "label": "This text shares traits with both human and AI writing, so the system is uncertain about its origin."
}
```
Note the original label and confidence score remained unchanged — only status and appeal_reasoning were added.

## Rate Limiting

The `/submit` endpoint is limited to **10 requests per minute and 100 per day**, per client, using 
Flask-Limiter with in-memory storage.

**Reasoning:** 10/minute comfortably covers a real writer submitting multiple drafts or revisions in 
one sitting, while still blocking a script attempting to flood the endpoint with rapid repeated calls. 
100/day allows for realistic heavy use across a full session without leaving the system open to abuse.

**Tested evidence** — sending 12 rapid requests in a loop:

The first 10 requests succeeded; requests 11 and 12 were correctly blocked with `429 Too Many Requests`.

## Audit Log

Every submission and appeal writes a structured JSON entry (via `GET /log`) containing: content ID, 
creator ID, timestamp, both individual signal scores, the combined confidence score, label, and status. 
Appeals add an `appeal_reasoning` field to the existing entry rather than creating a duplicate.

Sample entries from testing:
```json
{
  "content_id": "7b0ed5d9-eb28-4a60-91f7-ec8f237cc861",
  "creator_id": "test-user",
  "timestamp": "2026-07-08T03:19:06.267902+00:00",
  "signal1_score": 0.8,
  "signal2_score": 0.5,
  "confidence": 0.65,
  "label": "This text shares traits with both human and AI writing, so the system is uncertain about its origin.",
  "status": "classified"
},
{
  "content_id": "30679ec6-5114-4489-a570-33963cbfa435",
  "creator_id": "test-user",
  "timestamp": "2026-07-08T03:24:26.489863+00:00",
  "signal1_score": 0.8,
  "signal2_score": 0.5,
  "confidence": 0.65,
  "label": "This text shares traits with both human and AI writing, so the system is uncertain about its origin.",
  "status": "under_review",
  "appeal_reasoning": "I wrote this myself based on personal experience."
}
```

## Known Limitations

The stylometric signal (Signal 2) performs poorly on short text samples. In our own testing, a short 
generic-AI sample produced *higher* sentence-length variance than a longer, formal human sample — the 
opposite of what the metric is designed to detect — simply because a small number of sentences doesn't 
give the statistics enough data to stabilize. This is a known, documented limitation shared by 
commercial detection tools (e.g., Grammarly, Turnitin) on short inputs, not unique to this system. It's 
mitigated, but not eliminated, by averaging with the LLM signal.

## Spec Reflection

The spec's requirement to write planning.md *before* any code helped concretely: deciding the exact 
label text and confidence thresholds ahead of time meant the label-generation logic in `app.py` was a 
direct, mechanical translation of decisions already made, rather than something invented on the fly 
while coding.

One place implementation diverged slightly from the original plan: the plan assumed Signal 2's two 
sub-metrics (variance and vocabulary ratio) would behave consistently across sample sizes, but testing 
revealed they're unreliable on short text. The system still works as designed, but this is a case where 
hands-on testing surfaced a real limitation the planning phase didn't fully anticipate.

## AI Usage

1. **Flask app skeleton and signal function structure:** AI was directed to generate the initial 
`app.py` route structure and the `get_llm_signal()` function shape (API call + JSON parsing). The 
generated prompt template for Groq was reviewed and kept as-is since it matched the planned output 
format; the response-parsing logic was tested independently with three sample texts before being wired 
into the endpoint.

2. **Stylometric normalization formulas:** AI proposed the normalization approach for sentence length 
variance (capping at a variance of 10) and inverting the type-token ratio. This was reviewed and kept, 
but the resulting scores were tested against real samples, which revealed the short-text instability 
issue documented in Known Limitations above — a finding that came from hands-on testing, not from the 
AI-generated code itself.