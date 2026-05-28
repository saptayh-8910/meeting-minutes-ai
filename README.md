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

Input (81 words of standup notes):
```
Sapta: Can you have the tests done by Friday?
Yuki: Yes, I'll have them ready by Friday afternoon.
Sapta: Also we decided to use Claude Haiku for production to save costs.
Yuki: One issue - I still need access to the staging server.
Sapta: I'll request that today.
```

Output:
- **Action item**: Yuki → Complete API integration testing → Friday May 29
- **Action item**: Sapta → Request staging server access → Today May 28
- **Decision**: Use Claude Haiku for production deployment
- **Email draft**: Subject, summary, action table, ready to send

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

*Part of an AI engineering portfolio. [See all projects →](https://github.com/saptayh-8910)*
