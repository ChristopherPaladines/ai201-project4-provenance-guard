# Provenance Guard — Planning

## 1. Detection Signals

Signal 1 (Groq LLM)
- Measures: semantic/stylistic coherence
- Output: JSON with score (float 0–1, closer to 1 = more AI-like) + reason (short string explaining why)

Signal 2 (stylometric heuristics)
- Sentence length variance (AI = more uniform)
- Type-token ratio/vocab diversity (AI = more repetitive)
- Output: single float 0–1, computed by normalizing and averaging both metrics (same scale as Signal 1)

Combining Signal 1 + Signal 2 into one confidence score:
- Weighted 50/50: combined_score = (0.5 * signal1_score) + (0.5 * signal2_score)
- Chosen because both signals are treated as equally trustworthy until tested against real data

Why these two signals:
- Signal 1 uses the LLM to judge the text holistically, looking for patterns in how it reads overall.
- Signal 2 looks at the actual words used — how varied the vocabulary is, sentence length, and usage patterns — to measure structure mathematically rather than by "feel."
- Together they check two genuinely different things: one is semantic/holistic, the other is statistical/structural, so they catch different signals AI writing tends to leave behind.

## 2. Uncertainty Representation

What the score means:
The confidence score is a floating-point value between 0 and 1, not a binary flag. A binary output can't capture 
the underlying statistical nuance (e.g., text length, vocabulary patterns) that the signals actually measure, 
so a continuous score is needed to represent genuine uncertainty.

Thresholds:
- 0.00 – 0.40  →  high-confidence human
- 0.41 – 0.74  →  uncertain
- 0.75 – 1.00  →  high-confidence AI

Reasoning for thresholds:
The "likely AI" threshold is set deliberately high (0.75) rather than just above the midpoint, because a false 
positive (labeling a human's work as AI-generated) is worse than a false negative on a creative writing platform. 
Widening the "uncertain" range gives the system more room to stay cautious instead of confidently mislabeling 
borderline cases.

Validation plan:
Once both signals are implemented, thresholds will be tested against known AI-generated text, known human-written 
text, and borderline cases (Milestone 4) to confirm scores land where intuition expects. Thresholds will be 
adjusted if results don't match.

## 3. Transparency Label Design

All three labels share a consistent wrapper, followed by the specific verdict:

"Analyzation complete: The system has reviewed the text."

- High-confidence human (score 0.00–0.40):
  "This text is highly likely to be written by a human."

- Uncertain (score 0.41–0.74):
  "This text shares traits with both human and AI writing, so the system is uncertain about its origin."

- High-confidence AI (score 0.75–1.00):
  "This text shows a high presence of AI-generated patterns."

## 4. Appeals Workflow

Who can appeal:
Only content labeled "uncertain" or "likely AI" can be appealed. "Likely human" results are not appealable, 
since there's no meaningful reason for a creator to contest being classified as human.

What they submit:
- content_id
- creator_reasoning (free text explaining why they believe the classification is wrong)

What the system does on appeal:
- The original label and score are NOT changed or re-calculated (automated re-classification is not required).
- The content's status field changes from "classified" to "under_review."
- The appeal is logged alongside the original decision (same record or linked entry), so both are visible together.

What a reviewer sees in the appeal queue:
- The original submitted text
- The original label and confidence score
- The creator's reasoning, highlighted next to the original decision

## 5. Anticipated Edge Cases

Case 1: Genre-appropriate uniform writing
A well-written technical report, legal document, or academic essay may use repetitive terminology and uniform 
sentence structure intentionally, for clarity, not because it was AI-generated. Signal 2 (sentence length 
variance + type-token ratio) can't distinguish between "AI-uniform" and "intentionally uniform for genre 
reasons," so this kind of writing risks being pushed toward a false "likely AI" score.

Case 2: LLM signal is a black box
Signal 1 (Groq LLM) doesn't do a database lookup or pattern match we can inspect — it makes a holistic judgment 
based on what it learned during training. If a human's natural writing style happens to resemble common 
AI-associated phrasing habits (e.g., frequent use of formal transitions), the LLM may score it as AI-like, and 
we have no way to verify or override the internal reasoning — we can only see the "reason" text it chooses to 
return, not inspect how it actually arrived at the score.


## Architecture

### Submission Flow Narrative

Step 1 — Endpoint (takes text request):
Introduction to the backend system, where the user's content is accepted for processing.

Step 2 — Signal Detection 1 (Groq LLM):
The user's request is handed off to Groq for review. Groq returns a score based on its own 
judgment of how AI-like or human-like the text reads, along with a short reason.

Step 3 — Signal Detection 2 (heuristic/stylistic):
Using the input text itself to determine the frequency and structural patterns of the content, 
compiling a numeric value based on sentence length variance and vocabulary diversity.

Step 4 — Confidence Scoring:
Using both signals for each input is necessary. The system takes the score from each signal and 
weights them equally at 50% each, then combines them into one final confidence score.

Step 5 — Transparency Label:
The combined confidence score is compared against the thresholds defined earlier to determine 
the label: likely human, uncertain, or likely AI.

Step 6 — Audit Log:
Each input creates a unique content ID and timestamp so the submission is traceable. The audit 
log also saves both individual signal scores, the combined score, and the resulting label/status.

Step 7 — Response:
The system sends a JSON response back to the user through the same endpoint, containing the 
content ID, the label based on the confidence score, and the score itself.
 
SUBMISSION FLOW
===============

   [User]
     |
     | raw text
     v
POST /submit  ---------------------------------------------+
     |                                                      |
     | raw text                                             |
     v                                                      |
+---------------------+                                     |
| Signal 1: Groq LLM  |--- score + reason (0-1) ---+        |
+---------------------+                            |        |
                                                    v        |
+---------------------+                     +--------------+|
| Signal 2: Heuristics|--- score (0-1) ---->| Confidence   ||
+---------------------+                     | Scoring      ||
                                             | (50/50 avg)  ||
                                             +--------------+|
                                                    |         |
                                                    | combined score
                                                    v         |
                                          +-------------------+
                                          | Transparency Label |
                                          | (threshold check)  |
                                          +-------------------+
                                                    |
                                                    | content_id, score, label
                                                    v
                                          +-------------------+
                                          |    Audit Log      |
                                          +-------------------+
                                                    |
                                                    | JSON response
                                                    v
                                                 [User]


APPEAL FLOW
===========

   [User]
     |
     | content_id + creator_reasoning
     v
POST /appeal
     |
     | status: "under_review"
     v
+-------------------+
| Update Status      |
+-------------------+
     |
     | linked to original decision
     v
+-------------------+
|   Audit Log        |
+-------------------+
     |
     | confirmation JSON
     v
   [User]


## AI Tool Plan

### M3 — Submission endpoint + Signal 1
- Sections I'll provide: Detection Signals (Signal 1) + Architecture diagram
- What I'll ask for: Flask app skeleton with POST /submit route stub, plus the Groq signal 
  function (returning score + reason as JSON)
- How I'll verify: Call the signal function directly with a few sample texts before wiring it 
  into the endpoint, and confirm the output shape matches my spec (float 0-1 + reason string)

### M4 — Signal 2 + Confidence Scoring
- Sections I'll provide: Detection Signals (Signal 2) + Uncertainty Representation + diagram
- What I'll ask for: the stylometric heuristic function (sentence length variance + type-token 
  ratio, normalized to 0-1) and the 50/50 scoring logic that combines both signals
- How I'll verify: Test with a clearly-AI sample, a clearly-human sample, and two borderline 
  samples — confirm scores land in the ranges I'd expect and match my thresholds (0-0.40 / 
  0.41-0.74 / 0.75-1.00)

### M5 — Production layer (labels, appeals, rate limiting, audit log)
- Sections I'll provide: Transparency Label Design + Appeals Workflow + diagram
- What I'll ask for: the label-generation function (mapping score ranges to my 3 exact label 
  texts) and the POST /appeal endpoint
- How I'll verify: Submit inputs that produce all 3 label variants and confirm the exact text 
  matches my spec; submit a test appeal and confirm status changes to "under_review" and the 
  appeal is visible in GET /log
