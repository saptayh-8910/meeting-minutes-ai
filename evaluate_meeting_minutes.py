"""
evaluate.py — Meeting Minutes AI Evaluation
============================================
Tests extraction quality against human-labeled ground truth.

Metrics:
  - Action item recall     : % of expected actions correctly extracted
  - Owner accuracy         : % of extracted actions with correct owner
  - Decision recall        : % of expected decisions captured
  - Blocker recall         : % of expected blockers captured
  - Email quality score    : LLM-as-judge (1–10)
  - Overall score          : weighted average

Usage:
  pip install anthropic python-dotenv
  ANTHROPIC_API_KEY=... python evaluate.py
"""

import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

# ── Ground truth test cases ───────────────────────────────────────────
# Each case has a transcript + the expected extraction results.
# A human (you) labeled these — that's what makes evaluation meaningful.

TEST_CASES = [
    {
        "id": "TC01",
        "name": "Q2 Product Planning — AI Customer Support",
        "transcript": """Meeting: Q2 Product Planning — AI Customer Support Initiative
Date: May 27, 2026
Attendees: Sapta (PM), Yuki (Engineering Lead), Kenji (Designer), Maria (Marketing)

Sapta: Let's start. The main topic today is the AI customer support bot we're planning to launch for our SME clients in Japan.
Yuki: I've reviewed the technical requirements. We can build the RAG-based system using LangChain and ChromaDB. The embedding model we'll use is multilingual-e5-large to support Japanese and English.
Kenji: From the design side, I've drafted three UI concepts. I think we should go with the clean chat interface.
Maria: Marketing-wise, we should target restaurants and small retailers first. They get the most repetitive customer inquiries.
Sapta: Good insight. So let's decide — we'll target the food and retail SME segment for the pilot.
Yuki: For timeline, I need two weeks to set up the infrastructure and another week for testing. So we're looking at a June 20th launch date if we start next Monday.
Maria: I need the landing page ready by June 15th to start pre-launch marketing. Kenji, can you have the designs done by June 10th?
Kenji: June 10th works for me. I'll prioritize the mobile design since most SME owners check things on their phones.
Sapta: Agreed. Let's also make sure we have a proper Japanese FAQ document ready — Yuki, can you work with Maria on that?
Yuki: Sure. We'll need about 50 FAQ pairs to start. I'll draft the structure and Maria can fill in the content. Let's aim for June 7th for the FAQ draft.
Maria: That works. Also, should we offer a free trial period?
Sapta: I think 14 days is standard. Let's go with that.
Yuki: One thing I'm not sure about — should we use Claude Haiku or Sonnet for production?
Sapta: Let's start with Haiku for cost reasons and we can upgrade based on user feedback.
Maria: What about pricing? We haven't decided that yet.
Sapta: Let's table that for next week — I need to do more competitor research first. Can everyone send me their input on pricing by Friday?
Yuki: We need AWS credentials for the production deployment. I've requested them from IT but haven't heard back.
Sapta: I'll follow up with IT today. That's a blocker we need resolved ASAP.
Kenji: I also need user interview slots — can Marketing set up 3 sessions with potential customers?
Maria: I'll set up 3 customer interviews for the week of June 3rd.""",

        "expected": {
            "attendees": ["Sapta", "Yuki", "Kenji", "Maria"],
            "action_items": [
                {"owner": "Yuki", "action": "draft FAQ structure"},
                {"owner": "Maria", "action": "fill FAQ content"},
                {"owner": "Kenji", "action": "complete UI designs"},
                {"owner": "Maria", "action": "set up customer interviews"},
                {"owner": "Maria", "action": "prepare landing page"},
                {"owner": "Sapta", "action": "follow up with IT for AWS credentials"},
                {"owner": "Everyone", "action": "send pricing input to Sapta"},
            ],
            "decisions": [
                "target food and retail SME segment for pilot",
                "start with Claude Haiku for production",
                "offer 14-day free trial",
            ],
            "blockers": [
                "AWS credentials not received from IT",
            ],
            "open_questions": [
                "pricing model",
                "Haiku vs Sonnet final decision",
            ]
        }
    },
    {
        "id": "TC02",
        "name": "Engineering Sprint Planning",
        "transcript": """Sprint Planning Meeting — Engineering Team
Date: June 1, 2026
Attendees: Hiroshi (Engineering Manager), Akemi (Backend), Taro (Frontend), Priya (QA)

Hiroshi: This sprint we need to finish the payment integration and fix the performance issues.
Akemi: I can take the Stripe payment API integration. Should be done by June 8th. But I need the API keys from finance first.
Taro: I'll work on the checkout UI. I need Akemi's API endpoints before I can finish — so I'm blocked until she's done.
Hiroshi: Let's plan for Akemi to finish the backend by June 6th so Taro has two days buffer.
Akemi: That works. June 6th for the backend.
Priya: I'll write the test plan for payment flows. I can start that independently. Done by June 7th.
Hiroshi: Good. What about the performance issue on the search page?
Taro: I investigated — it's a missing database index. Akemi, can you add that?
Akemi: Yes, I'll do it today.
Hiroshi: So that's a blocker for users right now — let's mark it critical. Priya, can you verify the fix once Akemi deploys?
Priya: Yes, I'll verify same day.
Hiroshi: One open question — should we upgrade to PostgreSQL 16? I don't have a clear answer yet. Let's research and decide next sprint.
Taro: Also, the mobile responsive design isn't done. I deprioritized it last sprint. Should I pick it up this sprint?
Hiroshi: Let's defer it — payment integration is higher priority. We'll add it to next sprint backlog.
Priya: Do we have staging environment access? I've been testing on local only.
Hiroshi: That's on me — I'll set up staging access for Priya by end of day tomorrow.""",

        "expected": {
            "attendees": ["Hiroshi", "Akemi", "Taro", "Priya"],
            "action_items": [
                {"owner": "Akemi", "action": "Stripe payment API integration"},
                {"owner": "Akemi", "action": "add missing database index"},
                {"owner": "Taro", "action": "checkout UI"},
                {"owner": "Priya", "action": "write test plan for payment flows"},
                {"owner": "Priya", "action": "verify database index fix"},
                {"owner": "Hiroshi", "action": "set up staging access for Priya"},
            ],
            "decisions": [
                "defer mobile responsive design to next sprint",
                "Akemi finishes backend by June 6th",
            ],
            "blockers": [
                "Akemi needs API keys from finance",
                "Taro blocked until Akemi's API endpoints are ready",
                "search page performance issue (missing database index)",
            ],
            "open_questions": [
                "whether to upgrade to PostgreSQL 16",
            ]
        }
    },
    {
        "id": "TC03",
        "name": "Marketing Campaign Review",
        "transcript": """Marketing Review — Q2 Campaign
Date: June 2, 2026
Attendees: Yuna (Marketing Director), Ben (Content), Chloe (Paid Ads), David (Analytics)

Yuna: Let's review last month's campaign performance and plan June.
David: May numbers: 12,000 impressions, 340 clicks, 2.8% CTR. Conversion rate was 1.2% — below our 2% target.
Yuna: That's a problem. Chloe, what happened with paid?
Chloe: CPC went up 40% on Google — competition increased. We stayed within budget but got fewer clicks.
Yuna: Decision: we're shifting 30% of paid budget to LinkedIn for B2B targeting. Chloe, implement that starting June 5th.
Chloe: Got it. I'll need the new ad creatives from Ben.
Ben: I can have 3 LinkedIn ad variants ready by June 4th.
Yuna: Good. David, can you set up LinkedIn conversion tracking?
David: Yes, I'll have tracking live by June 5th.
Yuna: We also need a blog post about the Japan SME market — Ben, can you write that?
Ben: Sure. I'll need the customer interview data from Sales though. They promised it two weeks ago and still haven't sent it.
Yuna: That's a blocker — I'll chase Sales today. Ben, plan for June 10th assuming we get the data.
Chloe: One question — are we targeting Tokyo only or all of Japan for the LinkedIn campaign?
Yuna: All of Japan, but let's A/B test Tokyo vs national. David, set that up in the tracking.
David: Will do.
Yuna: Budget question — do we have approval for an extra ¥200,000 for June? I submitted the request but haven't heard back.
Ben: Also — should we post on Qiita or note.com for the Japan tech audience? No decision yet.""",

        "expected": {
            "attendees": ["Yuna", "Ben", "Chloe", "David"],
            "action_items": [
                {"owner": "Chloe", "action": "shift 30% paid budget to LinkedIn"},
                {"owner": "Ben", "action": "create 3 LinkedIn ad variants"},
                {"owner": "David", "action": "set up LinkedIn conversion tracking"},
                {"owner": "Ben", "action": "write blog post about Japan SME market"},
                {"owner": "Yuna", "action": "chase Sales for customer interview data"},
                {"owner": "David", "action": "set up Tokyo vs national A/B test"},
            ],
            "decisions": [
                "shift 30% of paid budget to LinkedIn",
                "A/B test Tokyo vs national targeting",
                "target all of Japan for LinkedIn campaign",
            ],
            "blockers": [
                "Sales has not sent customer interview data",
                "extra budget approval pending",
            ],
            "open_questions": [
                "Qiita vs note.com for Japan tech audience",
                "budget approval for extra 200,000 yen",
            ]
        }
    }
]

# ── Core extraction (mirrors app.py logic, without Streamlit) ─────────

def extract_minutes(transcript: str, client: Anthropic) -> dict:
    results = {}

    # Step 1: Summary
    r = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=1024,
        messages=[{"role": "user", "content": f"""Analyse this transcript and return ONLY valid JSON:
{{
  "title": "...",
  "date": "...",
  "attendees": ["..."],
  "summary": "2-3 sentence executive summary",
  "topics": ["topic 1", "topic 2"]
}}

Transcript:
{transcript}"""}]
    )
    try:
        raw = r.content[0].text.strip().strip("```json").strip("```").strip()
        results["summary"] = json.loads(raw)
    except:
        results["summary"] = {"title": "", "date": "", "attendees": [], "summary": "", "topics": []}

    # Step 2: Actions
    r = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=1024,
        messages=[{"role": "user", "content": f"""Extract all action items. Return ONLY valid JSON:
{{
  "action_items": [
    {{"owner": "Name", "action": "What to do", "deadline": "When or Not specified", "priority": "High|Medium|Low"}}
  ]
}}

Transcript:
{transcript}"""}]
    )
    try:
        raw = r.content[0].text.strip().strip("```json").strip("```").strip()
        results["actions"] = json.loads(raw)
    except:
        results["actions"] = {"action_items": []}

    # Step 3: Decisions
    r = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=1024,
        messages=[{"role": "user", "content": f"""Extract decisions, open questions, and blockers. Return ONLY valid JSON:
{{
  "decisions": ["..."],
  "open_questions": ["..."],
  "blockers": ["..."]
}}

Transcript:
{transcript}"""}]
    )
    try:
        raw = r.content[0].text.strip().strip("```json").strip("```").strip()
        results["decisions"] = json.loads(raw)
    except:
        results["decisions"] = {"decisions": [], "open_questions": [], "blockers": []}

    # Step 4: Email
    r = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=1024,
        messages=[{"role": "user", "content": f"""Write a professional meeting recap email (subject line + body).
Include action items with owners and deadlines. Be concise. No filler phrases.

Transcript:
{transcript}"""}]
    )
    results["email"] = r.content[0].text
    return results


# ── Scoring helpers ───────────────────────────────────────────────────

def fuzzy_match(extracted: str, expected: str, threshold: float = 0.4) -> bool:
    """Check if expected concept appears in extracted text (keyword overlap)."""
    extracted_lower = extracted.lower()
    expected_words = [w for w in expected.lower().split() if len(w) > 3]
    if not expected_words:
        return expected.lower() in extracted_lower
    matches = sum(1 for w in expected_words if w in extracted_lower)
    return matches / len(expected_words) >= threshold


def score_action_items(extracted_actions: list, expected_actions: list) -> dict:
    """
    Recall: what % of expected actions were extracted?
    Owner accuracy: of matched actions, what % have correct owner?
    """
    if not expected_actions:
        return {"recall": 1.0, "owner_accuracy": 1.0, "matched": 0, "total": 0}

    matched = 0
    owner_correct = 0

    for expected in expected_actions:
        exp_action = expected["action"]
        exp_owner = expected["owner"].lower()

        # Find best match in extracted
        best_match = None
        for ext in extracted_actions:
            ext_action = ext.get("action", "")
            if fuzzy_match(ext_action, exp_action):
                best_match = ext
                break

        if best_match:
            matched += 1
            ext_owner = best_match.get("owner", "").lower()
            # Owner match: exact or partial
            if exp_owner in ext_owner or ext_owner in exp_owner:
                owner_correct += 1

    recall = matched / len(expected_actions)
    owner_accuracy = owner_correct / matched if matched > 0 else 0.0

    return {
        "recall": round(recall, 3),
        "owner_accuracy": round(owner_accuracy, 3),
        "matched": matched,
        "total": len(expected_actions)
    }


def score_list_recall(extracted: list, expected: list) -> dict:
    """Generic recall: what % of expected items appear in extracted list?"""
    if not expected:
        return {"recall": 1.0, "matched": 0, "total": 0}

    matched = 0
    extracted_text = " ".join(str(e) for e in extracted).lower()

    for exp_item in expected:
        if fuzzy_match(extracted_text, exp_item):
            matched += 1

    return {
        "recall": round(matched / len(expected), 3),
        "matched": matched,
        "total": len(expected)
    }


def score_email_quality(email: str, transcript: str, client: Anthropic) -> float:
    """LLM-as-judge: score email quality 1-10."""
    try:
        r = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=100,
            messages=[{"role": "user", "content": f"""Rate this meeting recap email on a scale of 1-10.

Criteria:
- Does it include key action items with owners? (3 pts)
- Is the subject line clear? (2 pts)
- Is it concise and professional? (2 pts)
- Does it include next steps? (2 pts)
- No filler phrases? (1 pt)

Original transcript summary: {transcript[:300]}

Email to rate:
{email[:800]}

Respond with ONLY a number from 1-10."""}]
        )
        return min(max(float(r.content[0].text.strip()), 1), 10)
    except:
        return 5.0


def score_attendees(extracted: list, expected: list) -> float:
    if not expected:
        return 1.0
    extracted_text = " ".join(extracted).lower()
    matched = sum(1 for name in expected if name.lower() in extracted_text)
    return round(matched / len(expected), 3)


# ── Main evaluation loop ──────────────────────────────────────────────

def print_banner():
    print(f"""
{BLUE}{BOLD}╔══════════════════════════════════════════════════╗
║   Meeting Minutes AI — Evaluation Suite v1.0     ║
║   3 transcripts · Human-labeled ground truth     ║
╚══════════════════════════════════════════════════╝{RESET}
""")


def run_evaluation():
    print_banner()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(f"{RED}ANTHROPIC_API_KEY not set.{RESET}")
        return

    client = Anthropic(api_key=api_key)
    all_results = []
    aggregate = {
        "action_recall": [],
        "owner_accuracy": [],
        "decision_recall": [],
        "blocker_recall": [],
        "question_recall": [],
        "attendee_accuracy": [],
        "email_quality": [],
    }

    for i, tc in enumerate(TEST_CASES, 1):
        print(f"{BLUE}[{i}/{len(TEST_CASES)}] Running: {tc['name']}{RESET}")

        start = time.time()
        extracted = extract_minutes(tc["transcript"], client)
        elapsed = round(time.time() - start, 1)

        expected = tc["expected"]

        # Score each dimension
        action_scores = score_action_items(
            extracted["actions"].get("action_items", []),
            expected["action_items"]
        )
        decision_scores = score_list_recall(
            extracted["decisions"].get("decisions", []),
            expected["decisions"]
        )
        blocker_scores = score_list_recall(
            extracted["decisions"].get("blockers", []),
            expected["blockers"]
        )
        question_scores = score_list_recall(
            extracted["decisions"].get("open_questions", []),
            expected["open_questions"]
        )
        attendee_acc = score_attendees(
            extracted["summary"].get("attendees", []),
            expected["attendees"]
        )
        email_score = score_email_quality(
            extracted["email"], tc["transcript"], client
        )

        # Print per-test results
        def bar(score):
            filled = int(score * 15)
            color = GREEN if score >= 0.8 else YELLOW if score >= 0.6 else RED
            return f"{color}{'█' * filled}{'░' * (15 - filled)} {score:.2f}{RESET}"

        print(f"  Action recall      {bar(action_scores['recall'])}  ({action_scores['matched']}/{action_scores['total']})")
        print(f"  Owner accuracy     {bar(action_scores['owner_accuracy'])}")
        print(f"  Decision recall    {bar(decision_scores['recall'])}  ({decision_scores['matched']}/{decision_scores['total']})")
        print(f"  Blocker recall     {bar(blocker_scores['recall'])}  ({blocker_scores['matched']}/{blocker_scores['total']})")
        print(f"  Open Q recall      {bar(question_scores['recall'])}  ({question_scores['matched']}/{question_scores['total']})")
        print(f"  Attendee accuracy  {bar(attendee_acc)}")
        email_bar_score = email_score / 10
        print(f"  Email quality      {bar(email_bar_score)}  ({email_score:.1f}/10)")
        print(f"  ⏱  {elapsed}s\n")

        # Accumulate
        aggregate["action_recall"].append(action_scores["recall"])
        aggregate["owner_accuracy"].append(action_scores["owner_accuracy"])
        aggregate["decision_recall"].append(decision_scores["recall"])
        aggregate["blocker_recall"].append(blocker_scores["recall"])
        aggregate["question_recall"].append(question_scores["recall"])
        aggregate["attendee_accuracy"].append(attendee_acc)
        aggregate["email_quality"].append(email_score / 10)

        all_results.append({
            "test_case": tc["id"],
            "name": tc["name"],
            "elapsed_seconds": elapsed,
            "scores": {
                "action_recall": action_scores["recall"],
                "owner_accuracy": action_scores["owner_accuracy"],
                "decision_recall": decision_scores["recall"],
                "blocker_recall": blocker_scores["recall"],
                "open_question_recall": question_scores["recall"],
                "attendee_accuracy": attendee_acc,
                "email_quality": round(email_score / 10, 3),
            },
            "details": {
                "actions": action_scores,
                "decisions": decision_scores,
                "blockers": blocker_scores,
                "questions": question_scores,
            }
        })

        time.sleep(2)

    # ── Aggregate summary ─────────────────────────────────────────────
    def avg(lst): return round(sum(lst) / len(lst), 3) if lst else 0

    summary = {
        "action_recall":      avg(aggregate["action_recall"]),
        "owner_accuracy":     avg(aggregate["owner_accuracy"]),
        "decision_recall":    avg(aggregate["decision_recall"]),
        "blocker_recall":     avg(aggregate["blocker_recall"]),
        "open_q_recall":      avg(aggregate["question_recall"]),
        "attendee_accuracy":  avg(aggregate["attendee_accuracy"]),
        "email_quality":      avg(aggregate["email_quality"]),
    }
    overall = avg(list(summary.values()))

    print(f"{BLUE}{BOLD}{'═' * 56}{RESET}")
    print(f"{BOLD}  AGGREGATE RESULTS — {len(TEST_CASES)} test cases{RESET}")
    print(f"{BLUE}{BOLD}{'═' * 56}{RESET}\n")

    labels = {
        "action_recall":     "Action Item Recall",
        "owner_accuracy":    "Owner Accuracy",
        "decision_recall":   "Decision Recall",
        "blocker_recall":    "Blocker Recall",
        "open_q_recall":     "Open Question Recall",
        "attendee_accuracy": "Attendee Accuracy",
        "email_quality":     "Email Quality (÷10)",
    }

    for key, score in summary.items():
        label = labels[key]
        color = GREEN if score >= 0.8 else YELLOW if score >= 0.6 else RED
        bar_filled = int(score * 20)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        status = "✓ GOOD" if score >= 0.8 else "~ OK" if score >= 0.6 else "✗ NEEDS WORK"
        print(f"  {BOLD}{label:<26}{RESET} {color}{score:.3f}  [{bar}]  {status}{RESET}")

    overall_color = GREEN if overall >= 0.8 else YELLOW if overall >= 0.6 else RED
    print(f"\n  {BOLD}{'Overall Score':<26}{RESET} {overall_color}{overall:.3f}{RESET}")
    print(f"  {BOLD}{'Test Cases':<26}{RESET} {len(TEST_CASES)} (human-labeled)")
    print(f"  {BOLD}{'Model':<26}{RESET} claude-haiku-4-5-20251001 (extraction) + claude-sonnet-4-6 (email)")
    print(f"  {BOLD}{'Evaluated':<26}{RESET} {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    # ── Save results ──────────────────────────────────────────────────
    output = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "version": "1.0",
        "models": {
            "extraction": "claude-haiku-4-5-20251001",
            "email": "claude-sonnet-4-6"
        },
        "test_cases": len(TEST_CASES),
        "ground_truth_type": "human-labeled",
        "aggregate_scores": summary,
        "overall_score": overall,
        "per_test": all_results
    }

    with open("eval_results.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"  {GREEN}✓ Results saved to eval_results.json{RESET}")
    print(f"\n  {YELLOW}Add to README:{RESET}")
    print(f"  Action Recall: {summary['action_recall']:.1%} | Owner Accuracy: {summary['owner_accuracy']:.1%} | Email Quality: {summary['email_quality']*10:.1f}/10\n")


if __name__ == "__main__":
    run_evaluation()
