import os
import json
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

st.set_page_config(
    page_title="Meeting Minutes",
    page_icon="📝",
    layout="wide"
)

st.markdown("""
<style>
    .main { padding-top: 1rem; }

    .page-header {
        padding: 0 0 1rem 0;
        border-bottom: 1px solid rgba(128,128,128,0.2);
        margin-bottom: 1.5rem;
    }
    .page-header h1 {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0 0 4px 0;
    }
    .page-header p {
        font-size: 0.875rem;
        opacity: 0.6;
        margin: 0;
    }

    /* Action items */
    .action-row {
        display: flex;
        gap: 12px;
        align-items: flex-start;
        padding: 12px 0;
        border-bottom: 1px solid rgba(128,128,128,0.15);
    }
    .action-row:last-child { border-bottom: none; }
    .action-priority {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-top: 6px;
        flex-shrink: 0;
    }
    .priority-high { background: #ef4444; }
    .priority-medium { background: #f59e0b; }
    .priority-low { background: #22c55e; }
    .action-content { flex: 1; }
    .action-owner {
        font-size: 12px;
        font-weight: 600;
        opacity: 0.5;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .action-text {
        font-size: 14px;
        margin: 2px 0 4px;
        line-height: 1.4;
    }
    .action-deadline {
        font-size: 12px;
        opacity: 0.5;
    }

    /* Decisions */
    .decision-row {
        padding: 10px 0;
        border-bottom: 1px solid rgba(128,128,128,0.15);
        font-size: 14px;
        line-height: 1.5;
        display: flex;
        gap: 10px;
        align-items: flex-start;
    }
    .decision-row:last-child { border-bottom: none; }
    .decision-marker { opacity: 0.4; flex-shrink: 0; margin-top: 1px; }

    /* Section labels */
    .section-label {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        opacity: 0.45;
        margin: 1.25rem 0 0.5rem;
    }

    /* Summary box */
    .summary-text {
        font-size: 14px;
        line-height: 1.7;
        opacity: 0.85;
        padding: 12px 0;
    }

    /* Meta row */
    .meta-row {
        display: flex;
        gap: 24px;
        font-size: 13px;
        opacity: 0.55;
        padding-bottom: 12px;
        border-bottom: 1px solid rgba(128,128,128,0.15);
        margin-bottom: 4px;
        flex-wrap: wrap;
    }

    /* Blocker */
    .blocker-row {
        padding: 10px 12px;
        border-radius: 6px;
        border: 1px solid rgba(239,68,68,0.3);
        background: rgba(239,68,68,0.06);
        font-size: 14px;
        margin: 6px 0;
        color: #ef4444;
    }

    /* Question */
    .question-row {
        padding: 10px 0;
        border-bottom: 1px solid rgba(128,128,128,0.15);
        font-size: 14px;
        display: flex;
        gap: 10px;
        align-items: flex-start;
        opacity: 0.8;
    }
    .question-row:last-child { border-bottom: none; }
</style>
""", unsafe_allow_html=True)

SAMPLE_TRANSCRIPT = """Meeting: Q2 Product Planning — AI Customer Support Initiative
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

Sapta: Perfect. Let's wrap up. Next meeting is June 3rd, same time. I'll send the recap email."""

def extract_minutes(transcript, language, client):
    results = {}
    progress = st.progress(0)
    status = st.empty()
    lang_instruction = "Respond in Japanese." if language == "Japanese" else "Respond in English."

    # Step 1: Summary
    status.markdown("<span style='opacity:0.6; font-size:13px'>Step 1 of 4 — Summarising...</span>", unsafe_allow_html=True)
    r = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=1024,
        messages=[{"role": "user", "content": f"""{lang_instruction} Analyse this transcript and return ONLY valid JSON:
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
        results["summary"] = {"title":"Meeting","date":"","attendees":[],"summary":r.content[0].text,"topics":[]}
    progress.progress(25)

    # Step 2: Actions
    status.markdown("<span style='opacity:0.6; font-size:13px'>Step 2 of 4 — Extracting action items...</span>", unsafe_allow_html=True)
    r = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=1024,
        messages=[{"role": "user", "content": f"""{lang_instruction} Extract all action items. Return ONLY valid JSON:
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
        results["actions"] = {"action_items":[]}
    progress.progress(50)

    # Step 3: Decisions
    status.markdown("<span style='opacity:0.6; font-size:13px'>Step 3 of 4 — Identifying decisions...</span>", unsafe_allow_html=True)
    r = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=1024,
        messages=[{"role": "user", "content": f"""{lang_instruction} Extract decisions, open questions, and blockers. Return ONLY valid JSON:
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
        results["decisions"] = {"decisions":[],"open_questions":[],"blockers":[]}
    progress.progress(75)

    # Step 4: Email (Sonnet for quality)
    status.markdown("<span style='opacity:0.6; font-size:13px'>Step 4 of 4 — Drafting follow-up email...</span>", unsafe_allow_html=True)
    r = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=1024,
        messages=[{"role": "user", "content": f"""{lang_instruction} Write a professional meeting recap email (subject line + body). Include action items with owners and deadlines. Be concise. No filler phrases.

Transcript:
{transcript}"""}]
    )
    results["email"] = r.content[0].text
    progress.progress(100)
    status.empty()
    progress.empty()
    return results

# ── UI ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h1>Meeting Minutes</h1>
    <p>Paste a transcript — get structured minutes, action items, and a follow-up email.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("**Output language**")
    language = st.selectbox("", ["English", "Japanese"], label_visibility="collapsed")
    st.divider()
    st.markdown("""<div style='font-size:13px; opacity:0.6; line-height:1.8'>
    Steps 1–3: Claude Haiku<br>
    Step 4: Claude Sonnet<br><br>
    Extracts:<br>
    Action items + owners<br>
    Deadlines<br>
    Decisions made<br>
    Open questions<br>
    Blockers<br>
    Follow-up email
    </div>""", unsafe_allow_html=True)

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    if st.button("Load sample transcript", use_container_width=False):
        st.session_state.transcript = SAMPLE_TRANSCRIPT

    transcript = st.text_area(
        "Transcript",
        value=st.session_state.get("transcript", ""),
        height=420,
        placeholder="Paste meeting notes or transcript here...",
        label_visibility="collapsed"
    )

    wc = len(transcript.split()) if transcript else 0
    col_wc, col_btn = st.columns([1, 2])
    with col_wc:
        st.caption(f"{wc} words")
    with col_btn:
        run = st.button("Generate minutes →", type="primary", disabled=wc < 20, use_container_width=True)

    if run and wc >= 20:
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        results = extract_minutes(transcript, language, client)
        st.session_state.results = results

with col2:
    if "results" not in st.session_state:
        st.markdown("<div style='opacity:0.4; font-size:14px; padding-top:2rem'>Results appear here.</div>", unsafe_allow_html=True)
    else:
        r = st.session_state.results
        summary = r.get("summary", {})
        actions = r.get("actions", {}).get("action_items", [])
        decisions = r.get("decisions", {})
        email = r.get("email", "")

        tab1, tab2, tab3, tab4 = st.tabs([
            "Summary",
            f"Actions ({len(actions)})",
            "Decisions",
            "Email"
        ])

        with tab1:
            meta_parts = []
            if summary.get("date"): meta_parts.append(summary["date"])
            if summary.get("attendees"): meta_parts.append(", ".join(summary["attendees"]))
            if meta_parts:
                st.markdown(f"<div class='meta-row'>{'&nbsp;&nbsp;·&nbsp;&nbsp;'.join(meta_parts)}</div>", unsafe_allow_html=True)
            if summary.get("title"):
                st.markdown(f"**{summary['title']}**")
            if summary.get("summary"):
                st.markdown(f"<div class='summary-text'>{summary['summary']}</div>", unsafe_allow_html=True)
            if summary.get("topics"):
                st.markdown("<div class='section-label'>Topics covered</div>", unsafe_allow_html=True)
                for t in summary["topics"]:
                    st.markdown(f"<div class='decision-row'><span class='decision-marker'>—</span>{t}</div>", unsafe_allow_html=True)

        with tab2:
            if actions:
                for item in actions:
                    p = item.get("priority","Medium")
                    dot_class = "priority-high" if p=="High" else "priority-medium" if p=="Medium" else "priority-low"
                    st.markdown(f"""<div class='action-row'>
                        <div class='action-priority {dot_class}'></div>
                        <div class='action-content'>
                            <div class='action-owner'>{item.get('owner','TBD')}</div>
                            <div class='action-text'>{item.get('action','')}</div>
                            <div class='action-deadline'>{item.get('deadline','No deadline specified')}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown("<div style='opacity:0.5; font-size:14px'>No action items found.</div>", unsafe_allow_html=True)

        with tab3:
            dec = decisions.get("decisions", [])
            questions = decisions.get("open_questions", [])
            blockers = decisions.get("blockers", [])

            if dec:
                st.markdown("<div class='section-label'>Decided</div>", unsafe_allow_html=True)
                for d in dec:
                    st.markdown(f"<div class='decision-row'><span class='decision-marker'>✓</span>{d}</div>", unsafe_allow_html=True)

            if questions:
                st.markdown("<div class='section-label'>Open questions</div>", unsafe_allow_html=True)
                for q in questions:
                    st.markdown(f"<div class='question-row'><span class='decision-marker'>?</span>{q}</div>", unsafe_allow_html=True)

            if blockers:
                st.markdown("<div class='section-label'>Blockers</div>", unsafe_allow_html=True)
                for b in blockers:
                    st.markdown(f"<div class='blocker-row'>⚠ {b}</div>", unsafe_allow_html=True)

            if not dec and not questions and not blockers:
                st.markdown("<div style='opacity:0.5; font-size:14px'>Nothing extracted.</div>", unsafe_allow_html=True)

        with tab4:
            st.markdown(f"<div style='font-size:14px; line-height:1.7; white-space:pre-wrap'>{email}</div>", unsafe_allow_html=True)
            st.divider()
            st.download_button("Download email", data=email, file_name="recap.txt", mime="text/plain")

        st.divider()
        full = f"""MEETING MINUTES — {datetime.now().strftime('%Y-%m-%d %H:%M')}

{summary.get('title','')}
{summary.get('date','')}
Attendees: {', '.join(summary.get('attendees',[]))}

SUMMARY
{summary.get('summary','')}

TOPICS
{chr(10).join('- '+t for t in summary.get('topics',[]))}

ACTION ITEMS
{chr(10).join(f"[{i.get('priority','?')}] {i.get('owner','?')}: {i.get('action','')} — {i.get('deadline','no deadline')}" for i in actions)}

DECISIONS
{chr(10).join('- '+d for d in decisions.get('decisions',[]))}

OPEN QUESTIONS
{chr(10).join('- '+q for q in decisions.get('open_questions',[]))}

BLOCKERS
{chr(10).join('- '+b for b in decisions.get('blockers',[]))}

EMAIL DRAFT
{email}
"""
        st.download_button(
            "Download full minutes",
            data=full,
            file_name=f"minutes_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
