# Headline Classification Guide  
_Opinion vs News · Past vs Future Events (Zero-Shot MNLI, CPU-Only)_

## 1. Overview

This guide describes how to classify news **headlines** using open-source models that:

1. Detect whether a headline is **opinionated** or **straight news**.
2. Infer whether it is about a **past event**, **future event**, or a **general/timeless topic**.

Key constraints:

- **Open-source only**
- **Runs on CPU**
- **No custom training required** (for v1)
- **Headline-length inputs** (very short text)

The core idea is to use a **zero-shot natural language inference (NLI) model** (e.g. `facebook/bart-large-mnli` or a smaller MNLI variant) via Hugging Face’s `transformers` library.

---

## 2. Goals & Classification Tasks

### 2.1 Opinion vs News

For each headline, we want to answer:

- `is_opinion`: does this read like an editorial / opinion piece?
- `is_straight_news`: does this read like a neutral factual news report?

Examples:

**Opinion:**

- “Why the Fed Is Wrong About Inflation”
- “I Think Tech Stocks Are Still Overvalued”

**Straight news:**

- “Fed Raises Interest Rates by 25 Basis Points”
- “Apple Announces New iPhone Model”

### 2.2 Temporal Category (Past vs Future vs General)

For each headline, we want to categorize the **time focus** of the content:

- `PAST_EVENT` – Recapping something that already happened  
  - “Tesla Shares Surge After Yesterday’s Earnings Beat”
  - “Company X Filed for Bankruptcy in 2023”
- `FUTURE_EVENT` – Previewing something that is planned or expected  
  - “Tesla to Report Q4 Earnings Next Week”
  - “Fed Expected to Cut Rates in March”
- `GENERAL_TOPIC` – Analysis, evergreen, or ambiguous timing  
  - “How Tesla Changed the EV Market”
  - “The Outlook for Renewable Energy Stocks”

For v1, we can treat these as **soft labels** using scores and thresholds rather than hard ground truth.

---

## 3. Approach

We use a **zero-shot classification pipeline**:

- Model: a pre-trained NLI model (e.g. `facebook/bart-large-mnli`).
- Method: provide the headline as the **sequence** and a set of **candidate labels** (short natural-language descriptions of classes).
- Output: a probability for each label indicating how strongly the model believes the label is entailed by the headline.

We run **one zero-shot call per headline** with a combined label set that covers both:

- Opinion / straight news
- Past / future / general topic

Then we:

1. Convert scores into structured booleans (e.g. `is_opinion`, `is_past_event`).
2. Expose both the **booleans** and the **raw scores** for debugging/tuning.

---

## 4. Setup

### 4.1 Dependencies

```bash
pip install "transformers[torch]"
# or, if you already have torch:
# pip install transformers
