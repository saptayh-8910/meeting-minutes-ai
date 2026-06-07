# Meeting Minutes AI

Paste a meeting transcript. Get structured minutes, action items, and a follow-up email draft.

Built to solve a specific problem: meetings at Japanese tech companies generate discussion but rarely produce clean documentation. This tool does that in about 30 seconds.

---

## What it does

Takes raw meeting text — notes, transcripts, rough summaries — and runs it through four sequential AI calls:

1. Extracts the summary, attendees, and topics covered
2. Pulls out action items with owners and deadlines
3. Identifies decisions made and open questions left unresolved
4. Drafts a follow-up email ready to send

Steps 1–3 use Claude Haiku for speed. Step 4 uses Claude Sonnet because email quality matters.

---

## Example

Input (506 words — Q2 product planning meeting with 4 attendees):

```
Meeting: Q2 Product Planning — AI Customer Support Initiative
Date: May 27, 2026
Attendees: Sapta (PM), Yuki (Engineering Lead), Kenji (Designer), Maria (Marketing)

Sapta: Let's start. The main topic today is the AI customer support bot
we're planning to launch for our SME clients in Japan.
Yuki: I've reviewed the technical requirements. We can build the RAG-based
system using LangChain and ChromaDB...
...
Yuki: We need AWS credentials for the production deployment. I've requested
them from IT but haven't heard back.
Sapta: I'll follow up with IT today. That's a blocker we need resolved ASAP.
```

Output:

**Action items extracted (sample):**

| Owner | Action | Deadline | Priority |
|---|---|---|---|
| Yuki | Draft FAQ structure (50 pairs) with Maria | June 7 | High |
| Kenji | Complete mobile-first UI designs | June 10 | High |
| Maria | Set up 3 customer interviews for UI validation | Week of June 3 | High |
| Maria | Landing page ready for pre-launch marketing | June 15 | High |
| Sapta | Follow up with IT re: AWS credentials | Today | High |
| Everyone | Send pricing input to Sapta | Friday | Medium |

**Decisions made:**
- Target food and retail SME segment for the pilot
- Start with Claude Haiku for production; upgrade based on satisfaction scores
- Offer 14-day free trial period

**Open questions:**
- Pricing model (deferred to next week pending competitor research)
- Final model selection (Haiku vs Sonnet) based on user feedback

**Blockers:**
- AWS credentials for production deployment — requested from IT, no response yet

**Email draft:** Subject line, summary paragraph, action table, next meeting date — ready to send.

---

## Evaluation

Tested on 3 human-labeled transcripts with known action items, decisions, and blockers.

| Metric | Score |
|---|---|
| Action Item Recall | **100%** |
| Owner Accuracy | **84.1%** |
| Email Quality (LLM judge) | **8.0 / 10** |

Evaluation script: `evaluate_meeting_minutes.py` · Results: `eval_results.json`

---

## Setup

```bash
git clone https://github.com/saptayh-8910/meeting-minutes-ai.git
cd meeting-minutes-ai

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Add your Anthropic API key:
```
ANTHROPIC_API_KEY=your_key_here
```

Run:
```bash
streamlit run app.py
```

---

## Stack

- Streamlit — UI
- Anthropic Python SDK — direct API calls, no LangChain overhead
- Claude Haiku — steps 1–3 (fast, cheap)
- Claude Sonnet — step 4 (better writing quality for email)
- Prompt chaining — each step's output informs the next

---

## Design decisions

**Why prompt chaining instead of one big prompt?**
A single prompt asking for summary + actions + decisions + email produces mediocre results across all four. Separate focused prompts produce better results on each. The latency increase is worth it.

**Why Sonnet only for email?**
Email is the thing people actually send externally. The extra cost (~$0.003 per run) is justified. The other three steps are internal processing where Haiku's quality is sufficient.

**Why not use LangChain chains?**
The Anthropic SDK is simpler for linear chains. LangChain adds abstraction cost without benefit here.

**Dark/light mode**
Uses opacity-based CSS rather than hardcoded colors. Works in both modes without a separate theme.

---

## Limitations

- Works best with English and Japanese transcripts
- Needs speaker attribution (Name: text) for accurate action item ownership
- No audio transcription — text input only
- Does not connect to calendar, Slack, or email systems

---

## Japan market context

議事録 (meeting minutes) documentation is taken seriously in Japanese business culture. Most tools default to English patterns. This one outputs in whichever language the transcript is in, and the email draft uses appropriate keigo when set to Japanese.

---

## Project Structure

meeting-minutes-ai/
├── app.py                      # Main Streamlit application
├── evaluate_meeting_minutes.py # Evaluation script
├── eval_results.json           # Latest evaluation scores
├── requirements.txt
└── README.md
