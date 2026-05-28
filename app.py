import os
import json
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

st.set_page_config(
    page_title="Meeting Minutes AI",
    page_icon="📝",
    layout="wide"
)

st.markdown("""
<style>
    .main { padding-top: 0.5rem; }
    .header-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem;
        border: 1px solid #30363d;
    }
    .header-box h1 { color: white; margin: 0; font-size: 1.8rem; }
    .header-box p { color: #8b949e; margin: 4px 0 0; }
    .section-card {
        background: #f8f9fa; border-radius: 10px; padding: 16px;
        margin: 8px 0; border-left: 4px solid #0f3460;
    }
    .action-item {
        background: #fff3cd; border-radius: 8px; padding: 10px 14px;
        margin: 6px 0; border-left: 4px solid #ffc107;
    }
    .decision-item {
        background: #d4edda; border-radius: 8px; padding: 10px 14px;
        margin: 6px 0; border-left: 4px solid #28a745;
    }
    .question-item {
        background: #cce5ff; border-radius: 8px; padding: 10px 14px;
        margin: 6px 0; border-left: 4px solid #004085;
    }
    .step-badge {
        background: #0f3460; color: white; border-radius: 99px;
        padding: 3px 10px; font-size: 12px; font-weight: 600;
        display: inline-block; margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ── Sample meeting transcript ─────────────────────────────────────────
SAMPLE_TRANSCRIPT = """
Meeting: Q2 Product Planning — AI Customer Support Initiative
Date: May 27, 2026
Attendees: Sapta (PM), Yuki (Engineering Lead), Kenji (Designer), Maria (Marketing)

Sapta: Let's start. The main topic today is the AI customer support bot we're planning to launch for our SME clients in Japan.

Yuki: I've reviewed the technical requirements. We can build the RAG-based system using LangChain and ChromaDB. The embedding model we'll use is multilingual-e5-large to support Japanese and English.

Kenji: From the design side, I've drafted three UI concepts. I think we should go with the clean chat interface — it feels more trustworthy for Japanese users. I'll share the Figma link after this meeting.

Maria: Marketing-wise, we should target restaurants and small retailers first. They get the most repetitive customer inquiries. I talked to five potential customers last week and they all said the same thing — they spend 2-3 hours daily answering the same questions.

Sapta: Good insight. So let's decide — we'll target the food and retail SME segment for the pilot.

Yuki: For timeline, I need two weeks to set up the infrastructure and another week for testing. So we're looking at a June 20th launch date if we start next Monday.

Maria: I need the landing page ready by June 15th to start pre-launch marketing. Kenji, can you have the designs done by June 10th?

Kenji: June 10th works for me. I'll prioritize the mobile design since most SME owners check things on their phones.

Sapta: Agreed. Let's also make sure we have a proper Japanese FAQ document ready — Yuki, can you work with Maria on that?

Yuki: Sure. We'll need about 50 FAQ pairs to start. I'll draft the structure and Maria can fill in the content. Let's aim for June 7th for the FAQ draft.

Maria: That works. Also, should we offer a free trial period?

Sapta: Good question. I think 14 days is standard. Let's go with that.

Yuki: One thing I'm not sure about — should we use Claude Haiku or Sonnet for production? Haiku is faster and cheaper but Sonnet gives better quality.

Sapta: Let's start with Haiku for cost reasons and we can upgrade based on user feedback. We'll track the satisfaction scores.

Maria: What about pricing? We haven't decided that yet.

Sapta: Let's table that for next week — I need to do more competitor research first. Can everyone send me their input on pricing by Friday?

Yuki: Will do.

Kenji: Same.

Sapta: Great. Any other blockers?

Yuki: We need AWS credentials for the production deployment. I've requested them from IT but haven't heard back.

Sapta: I'll follow up with IT today. That's a blocker we need resolved ASAP.

Kenji: I also need user interview slots — can Marketing set up 3 sessions with potential customers so I can validate the UI designs?

Maria: I'll set up 3 customer interviews for the week of June 3rd. I'll send calendar invites today.

Sapta: Perfect. Let's wrap up. Next meeting is June 3rd, same time. I'll send the recap email.
"""

# ── Prompt chaining — 4 AI steps ─────────────────────────────────────
def extract_minutes(transcript, language, client):
    results = {}
    progress = st.progress(0)
    status = st.empty()

    # ── Step 1: Summary ────────────────────────────────────────────────
    status.markdown("**Step 1/4** — Generating meeting summary...")
    lang_instruction = "Respond in Japanese (日本語で回答してください)." if language == "Japanese" else "Respond in English."

    summary_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"""You are an expert meeting facilitator. {lang_instruction}

Analyze this meeting transcript and provide:
1. Meeting title and date (if mentioned)
2. Attendees list
3. A concise executive summary (3-4 sentences covering the main topic and outcomes)
4. Key topics discussed (bullet points)

Transcript:
{transcript}

Format your response as JSON:
{{
  "title": "...",
  "date": "...",
  "attendees": ["..."],
  "summary": "...",
  "topics": ["..."]
}}

Return ONLY valid JSON."""}]
    )
    try:
        raw = summary_response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        results["summary"] = json.loads(raw)
    except:
        results["summary"] = {"title": "Meeting", "date": "", "attendees": [], "summary": summary_response.content[0].text, "topics": []}
    progress.progress(25)

    # ── Step 2: Action items ───────────────────────────────────────────
    status.markdown("**Step 2/4** — Extracting action items...")
    action_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"""Extract ALL action items from this meeting transcript. {lang_instruction}

For each action item identify: who owns it, what they need to do, and the deadline (if mentioned).

Transcript:
{transcript}

Format as JSON:
{{
  "action_items": [
    {{
      "owner": "Person's name",
      "action": "What they need to do",
      "deadline": "Date or timeframe, or 'Not specified'",
      "priority": "High/Medium/Low"
    }}
  ]
}}

Return ONLY valid JSON."""}]
    )
    try:
        raw = action_response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        results["actions"] = json.loads(raw)
    except:
        results["actions"] = {"action_items": []}
    progress.progress(50)

    # ── Step 3: Decisions & questions ─────────────────────────────────
    status.markdown("**Step 3/4** — Identifying decisions and open questions...")
    decisions_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"""From this meeting transcript, extract: {lang_instruction}
1. Key decisions that were made (clear agreements reached)
2. Open questions or items parked for later discussion
3. Blockers or risks mentioned

Transcript:
{transcript}

Format as JSON:
{{
  "decisions": ["Decision 1", "Decision 2"],
  "open_questions": ["Question 1", "Question 2"],
  "blockers": ["Blocker 1"]
}}

Return ONLY valid JSON."""}]
    )
    try:
        raw = decisions_response.content[0].text.strip()
        if "```" in raw:
            raw = raw.split("```")[1].replace("json", "").strip()
        results["decisions"] = json.loads(raw)
    except:
        results["decisions"] = {"decisions": [], "open_questions": [], "blockers": []}
    progress.progress(75)

    # ── Step 4: Email draft ────────────────────────────────────────────
    status.markdown("**Step 4/4** — Drafting follow-up email...")
    email_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"""Write a professional meeting recap email. {lang_instruction}

Based on this transcript, write a concise, well-formatted email that:
- Has a clear subject line
- Summarizes key outcomes in 2-3 sentences
- Lists action items with owners and deadlines
- Lists key decisions made
- Notes any open questions for next meeting
- Is professional but friendly

Use Japanese business email etiquette if writing in Japanese (appropriate keigo).

Transcript:
{transcript}

Write just the email (subject line + body), no extra commentary."""}]
    )
    results["email"] = email_response.content[0].text
    progress.progress(100)

    status.empty()
    progress.empty()
    return results

# ══ MAIN UI ═══════════════════════════════════════════════════════════

st.markdown("""
<div class="header-box">
    <h1>📝 Meeting Minutes AI Agent</h1>
    <p>Paste your meeting transcript → Get structured minutes, action items, decisions, and a ready-to-send email · EN/JP対応</p>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    language = st.selectbox("Output Language", ["English", "Japanese"], help="Language for the generated minutes")
    model_info = st.expander("🤖 How it works")
    with model_info:
        st.markdown("""
        This agent uses **prompt chaining** — 4 sequential AI calls:

        1. **Summary Agent** → Meeting overview + topics
        2. **Action Extractor** → Who does what by when
        3. **Decision Tracker** → Decisions + open questions
        4. **Email Drafter** → Ready-to-send recap (uses Sonnet for quality)

        Each step builds on the previous one.
        """)

    st.divider()
    st.markdown("### 📋 What Gets Extracted")
    items = [
        "📌 Meeting summary",
        "✅ Action items + owners",
        "📅 Deadlines",
        "🔑 Key decisions",
        "❓ Open questions",
        "🚧 Blockers & risks",
        "📧 Follow-up email draft",
    ]
    for item in items:
        st.markdown(f"<div style='font-size:13px; padding:3px 0'>{item}</div>", unsafe_allow_html=True)

    st.divider()
    st.caption("Step 1-3: Claude Haiku (fast)")
    st.caption("Step 4: Claude Sonnet (quality email)")

# ── Main area ─────────────────────────────────────────────────────────
col_input, col_output = st.columns([1, 1])

with col_input:
    st.markdown("### 📥 Meeting Transcript")

    use_sample = st.button("⚡ Load Sample Transcript", use_container_width=True,
                           help="Load a sample product planning meeting")

    if use_sample:
        st.session_state.transcript = SAMPLE_TRANSCRIPT

    transcript = st.text_area(
        "Paste your meeting transcript here",
        value=st.session_state.get("transcript", ""),
        height=400,
        placeholder="Paste your meeting notes or transcript here...\n\nTip: Include speaker names, dates, and any mentioned deadlines for better results.",
        key="transcript_input"
    )

    word_count = len(transcript.split()) if transcript else 0
    st.caption(f"Word count: {word_count}")

    if transcript and word_count > 20:
        if st.button("🚀 Generate Meeting Minutes", type="primary", use_container_width=True):
            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            with st.spinner(""):
                results = extract_minutes(transcript, language, client)
            st.session_state.results = results
            st.success("✅ Minutes generated!")
    else:
        st.info("Load the sample transcript or paste your own, then click Generate.")

with col_output:
    st.markdown("### 📤 Generated Minutes")

    if "results" not in st.session_state:
        st.markdown("""
        **How to use:**
        1. Click **Load Sample Transcript** to see an example
        2. Or paste your own meeting notes
        3. Click **Generate Meeting Minutes**
        4. Download the results in multiple formats

        **Works best with:**
        - Team meetings with multiple speakers
        - Product planning sessions
        - Client calls with action items
        - 1:1s with follow-up tasks
        """)
    else:
        results = st.session_state.results
        summary = results.get("summary", {})
        actions = results.get("actions", {}).get("action_items", [])
        decisions = results.get("decisions", {})
        email = results.get("email", "")

        tab1, tab2, tab3, tab4 = st.tabs([
            f"📋 Summary",
            f"✅ Actions ({len(actions)})",
            f"🔑 Decisions",
            f"📧 Email Draft"
        ])

        with tab1:
            if summary.get("title"):
                st.markdown(f"**{summary['title']}**")
            if summary.get("date"):
                st.caption(f"📅 {summary['date']}")
            if summary.get("attendees"):
                st.markdown(f"**Attendees:** {', '.join(summary['attendees'])}")
            st.divider()
            if summary.get("summary"):
                st.markdown(f"**Executive Summary**\n\n{summary['summary']}")
            if summary.get("topics"):
                st.markdown("**Topics Discussed**")
                for topic in summary["topics"]:
                    st.markdown(f"- {topic}")

        with tab2:
            if actions:
                for i, item in enumerate(actions, 1):
                    priority_color = "🔴" if item.get("priority") == "High" else "🟡" if item.get("priority") == "Medium" else "🟢"
                    st.markdown(f"""<div class="action-item">
                        <strong>{priority_color} #{i} {item.get('owner', 'TBD')}</strong><br>
                        {item.get('action', '')}<br>
                        <small>📅 Deadline: {item.get('deadline', 'Not specified')}</small>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("No action items found.")

        with tab3:
            dec_list = decisions.get("decisions", [])
            questions = decisions.get("open_questions", [])
            blockers = decisions.get("blockers", [])

            if dec_list:
                st.markdown("**✅ Decisions Made**")
                for d in dec_list:
                    st.markdown(f"""<div class="decision-item">{d}</div>""", unsafe_allow_html=True)

            if questions:
                st.markdown("**❓ Open Questions / Parking Lot**")
                for q in questions:
                    st.markdown(f"""<div class="question-item">{q}</div>""", unsafe_allow_html=True)

            if blockers:
                st.markdown("**🚧 Blockers & Risks**")
                for b in blockers:
                    st.error(b)

        with tab4:
            st.markdown(email)
            st.download_button(
                "📋 Copy Email",
                data=email,
                file_name="meeting_recap_email.txt",
                mime="text/plain",
                use_container_width=True
            )

        # ── Download full minutes ──────────────────────────────────────
        st.divider()
        full_minutes = f"""MEETING MINUTES
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Language: {language}

{'='*50}
SUMMARY
{'='*50}
{summary.get('summary', '')}

Attendees: {', '.join(summary.get('attendees', []))}
Topics: {chr(10).join('- ' + t for t in summary.get('topics', []))}

{'='*50}
ACTION ITEMS
{'='*50}
{chr(10).join(f"[{i['priority']}] {i['owner']}: {i['action']} (Due: {i['deadline']})" for i in actions)}

{'='*50}
DECISIONS MADE
{'='*50}
{chr(10).join('- ' + d for d in decisions.get('decisions', []))}

{'='*50}
OPEN QUESTIONS
{'='*50}
{chr(10).join('- ' + q for q in decisions.get('open_questions', []))}

{'='*50}
FOLLOW-UP EMAIL DRAFT
{'='*50}
{email}
"""
        st.download_button(
            "📥 Download Full Minutes (.txt)",
            data=full_minutes,
            file_name=f"meeting_minutes_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
