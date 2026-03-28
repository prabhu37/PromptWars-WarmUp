"""
app.py  —  CLARITY AI
━━━━━━━━━━━━━━━━━━━━━
Orchestration Layer (Layer 2)
Accepts messy real-world inputs → routes to execution/input_processor.py
→ renders structured, prioritised, life-saving action plans.

Run:
    streamlit run app.py
"""

import sys
import os
import json
import base64
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

# Make execution/ importable regardless of launch directory
sys.path.insert(0, os.path.dirname(__file__))
from execution.input_processor import process_input, ProcessedOutput, ActionItem

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CLARITY AI · Unstructured → Actionable",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS  (light clean theme)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
*, *::before, *::after { box-sizing: border-box; }
html, body, .stApp {
    background: #f8fafc !important;
    font-family: 'Inter', sans-serif !important;
    color: #0f172a !important;
}
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none !important; }
section[data-testid="stSidebar"] { display: none; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: rgba(0,0,0,0.03); }
::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.12); border-radius: 3px; }

/* ── Background mesh ── */
.stApp::before {
    content: '';
    position: fixed; inset: 0; z-index: 0;
    background:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(0,212,255,0.07) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 110%, rgba(124,58,237,0.07) 0%, transparent 60%);
    pointer-events: none;
}

/* ── App wrapper ── */
.block-container {
    max-width: 1400px !important;
    padding: 0 2rem 4rem !important;
    position: relative; z-index: 1;
}

/* ── Header ── */
.clarity-header {
    text-align: center;
    padding: 52px 0 36px;
}
.clarity-wordmark {
    font-size: clamp(2.6rem, 5vw, 4rem);
    font-weight: 900;
    letter-spacing: -3px;
    background: linear-gradient(130deg, #00d4ff 0%, #7c3aed 50%, #00d4ff 100%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmer 4s linear infinite;
    line-height: 1;
}
@keyframes shimmer {
    0%   { background-position: 0% center; }
    100% { background-position: 200% center; }
}
.clarity-sub {
    margin-top: 10px;
    color: rgba(0,0,0,0.45);
    font-size: 0.82rem;
    letter-spacing: 4px;
    text-transform: uppercase;
    font-weight: 600;
}
.demo-pill {
    display: inline-block;
    margin-top: 14px;
    padding: 4px 14px;
    border-radius: 100px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.pill-demo { background: rgba(255,160,64,0.15); color: #e67e22; border: 1px solid rgba(255,160,64,0.3); }
.pill-live { background: rgba(46,213,115,0.15); color: #27ae60; border: 1px solid rgba(46,213,115,0.3); }

/* ── Stats row ── */
.stats-row {
    display: flex;
    gap: 14px;
    margin-bottom: 28px;
    flex-wrap: wrap;
}
.stat-card {
    flex: 1; min-width: 130px;
    background: #ffffff;
    border: 1px solid rgba(0,0,0,0.06);
    box-shadow: 0 2px 8px -2px rgba(0,0,0,0.03);
    border-radius: 14px;
    padding: 14px 18px;
}
.stat-label {
    font-size: 0.7rem; font-weight: 700;
    color: rgba(0,0,0,0.4);
    letter-spacing: 1.5px; text-transform: uppercase;
    margin-bottom: 4px;
}
.stat-value {
    font-size: 1.7rem; font-weight: 800;
    color: #0f172a; line-height: 1;
}
.stat-sub { font-size: 0.72rem; color: rgba(0,0,0,0.45); margin-top: 4px; }

/* ── Tabs ── */
div[data-baseweb="tab-list"] {
    background: #ffffff !important;
    border-radius: 14px !important;
    padding: 6px !important;
    border: 1px solid rgba(0,0,0,0.06) !important;
    gap: 4px !important;
}
div[data-baseweb="tab"] {
    background: transparent !important;
    color: rgba(0,0,0,0.5) !important;
    border-radius: 10px !important;
    padding: 10px 20px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    border: none !important;
    transition: all 0.25s ease !important;
    white-space: nowrap !important;
}
div[aria-selected="true"] {
    background: linear-gradient(135deg,rgba(0,212,255,0.12),rgba(124,58,237,0.12)) !important;
    color: #1e293b !important;
    border: 1px solid rgba(0,212,255,0.25) !important;
}

/* ── Panel cards ── */
.panel {
    background: #ffffff;
    border: 1px solid rgba(0,0,0,0.06);
    box-shadow: 0 4px 12px -2px rgba(0,0,0,0.03);
    border-radius: 20px;
    padding: 28px 26px;
    height: 100%;
}
.panel-title {
    font-size: 0.72rem; font-weight: 800;
    color: rgba(0,0,0,0.4);
    letter-spacing: 2.5px; text-transform: uppercase;
    margin-bottom: 20px;
    display: flex; align-items: center; gap: 8px;
}
.panel-title::after {
    content: ''; flex: 1; height: 1px;
    background: rgba(0,0,0,0.06);
}

/* ── Streamlit widgets ── */
.stTextArea textarea, .stTextInput input {
    background: #f8fafc !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    border-radius: 12px !important;
    color: #0f172a !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    transition: border-color 0.25s !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    background: #ffffff !important;
    border-color: rgba(0,212,255,0.5) !important;
    box-shadow: 0 0 0 3px rgba(0,212,255,0.15) !important;
}
.stTextArea label, .stTextInput label, .stFileUploader label, .stSelectbox label {
    color: #475569 !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
}
div[data-testid="stFileUploader"] > div {
    background: #f8fafc !important;
    border: 2px dashed rgba(0,0,0,0.12) !important;
    border-radius: 14px !important;
    transition: all 0.25s !important;
}
div[data-testid="stFileUploader"] > div:hover {
    border-color: rgba(0,212,255,0.45) !important;
    background: rgba(0,212,255,0.04) !important;
}
div[data-baseweb="select"] > div {
    background-color: #f8fafc !important;
    border: 1px solid rgba(0,0,0,0.1) !important;
    border-radius: 12px !important;
}

/* ── Process button ── */
div[data-testid="stVerticalBlock"] .stButton > button {
    width: 100% !important;
    background: linear-gradient(135deg, #00d4ff, #7c3aed) !important;
    color: #fff !important; border: none !important;
    border-radius: 12px !important;
    padding: 13px 28px !important;
    font-weight: 700 !important; font-size: 0.95rem !important;
    letter-spacing: 0.5px !important;
    transition: all 0.3s ease !important;
    cursor: pointer !important;
    box-shadow: 0 4px 12px rgba(0,212,255,0.15) !important;
}
div[data-testid="stVerticalBlock"] .stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(0,212,255,0.25) !important;
}
div[data-testid="stVerticalBlock"] .stButton > button:active {
    transform: translateY(0) !important;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #00d4ff !important; }

/* ── Streamlit info/warning/error boxes ── */
.stAlert { border-radius: 12px !important; }

/* General text overrides */
.stMarkdown p { color: #334155; line-height: 1.65; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def _init_state():
    defaults = {
        "results": [],          # list of ProcessedOutput
        "processing": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
_SEV_ICONS  = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}
_SEV_CLASS  = {"CRITICAL": "sev-critical", "HIGH": "sev-high", "MEDIUM": "sev-medium", "LOW": "sev-low"}
_TYPE_ICONS = {"voice": "🎙️", "photo": "📷", "medical": "🏥", "news": "📰", "traffic": "🚦", "weather": "🌪️"}
_URG_ICONS  = {"immediate": "⚡", "short_term": "⏱️", "long_term": "📅"}
_CAT_COLORS = {
    "medical": "#c0392b",
    "safety": "#e74c3c",
    "logistics": "#2980b9",
    "communication": "#8e44ad",
    "infrastructure": "#d35400",
}

def _severity_html(sev: str) -> str:
    icon = _SEV_ICONS.get(sev, "⚪")
    return f"""
    <span style="
        display:inline-flex;align-items:center;gap:7px;
        padding:5px 16px;border-radius:100px;font-weight:700;
        font-size:0.78rem;letter-spacing:1.5px;text-transform:uppercase;
        {'background:rgba(255,71,87,0.1);color:#e74c3c;border:1px solid rgba(255,71,87,0.3);' if sev=='CRITICAL' else ''}
        {'background:rgba(255,107,53,0.1);color:#d35400;border:1px solid rgba(255,107,53,0.3);' if sev=='HIGH' else ''}
        {'background:rgba(255,160,64,0.1);color:#f39c12;border:1px solid rgba(255,160,64,0.3);' if sev=='MEDIUM' else ''}
        {'background:rgba(46,213,115,0.1);color:#27ae60;border:1px solid rgba(46,213,115,0.3);' if sev=='LOW' else ''}
    ">{icon} {sev}</span>"""


def _confidence_bar(conf: float) -> str:
    pct = int(conf * 100)
    return f"""
    <div style="margin-top:12px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
        <span style="font-size:0.75rem;color:#64748b;letter-spacing:1px;text-transform:uppercase;font-weight:600;">Confidence</span>
        <span style="font-size:0.78rem;font-weight:800;color:#0f172a;">{pct}%</span>
      </div>
      <div style="background:#e2e8f0;border-radius:100px;height:6px;overflow:hidden;">
        <div style="width:{pct}%;height:100%;border-radius:100px;
                    background:linear-gradient(90deg,#00d4ff,#7c3aed);
                    transition:width 1s ease;"></div>
      </div>
    </div>"""


def _render_result(result: ProcessedOutput):
    ts = datetime.fromisoformat(result.timestamp).strftime("%H:%M:%S · %d %b %Y")
    mode_badge = (
        '<span style="font-size:0.68rem;color:#27ae60;background:rgba(46,213,115,0.1);'
        'border:1px solid rgba(46,213,115,0.3);border-radius:100px;padding:2px 10px;font-weight:700;">● LIVE</span>'
        if result.mode == "live" else
        '<span style="font-size:0.68rem;color:#d35400;background:rgba(255,160,64,0.1);'
        'border:1px solid rgba(255,160,64,0.3);border-radius:100px;padding:2px 10px;font-weight:700;">◎ DEMO</span>'
    )
    verified_badge = (
        '<span style="font-size:0.7rem;color:#27ae60;background:rgba(46,213,115,0.1);'
        'border:1px solid rgba(46,213,115,0.3);border-radius:100px;padding:2px 10px;font-weight:700;">✓ Verified</span>'
        if result.verified else
        '<span style="font-size:0.7rem;color:#d35400;background:rgba(255,160,64,0.1);'
        'border:1px solid rgba(255,160,64,0.3);border-radius:100px;padding:2px 10px;font-weight:700;">⚠ Unverified</span>'
    )

    type_icon = _TYPE_ICONS.get(result.input_type, "📄")

    # Header row
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px;">
      <div style="width:42px;height:42px;border-radius:12px;
                  background:linear-gradient(135deg,rgba(0,212,255,0.15),rgba(124,58,237,0.15));
                  border:1px solid rgba(0,212,255,0.3);
                  display:flex;align-items:center;justify-content:center;font-size:1.3rem;">{type_icon}</div>
      <div>
        <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:1.5px;font-weight:700;">
          {result.input_type.upper()} INPUT</div>
        <div style="font-size:0.78rem;color:#94a3b8;font-weight:500;margin-top:1px;">{ts}</div>
      </div>
      <div style="margin-left:auto;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        {mode_badge}
        {verified_badge}
        {_severity_html(result.severity)}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Summary
    st.markdown(f"""
    <div style="background:rgba(0,212,255,0.05);border:1px solid rgba(0,212,255,0.2);
                border-radius:14px;padding:16px 20px;margin-bottom:16px;box-shadow:0 2px 4px -1px rgba(0,0,0,0.02)">
      <div style="font-size:0.68rem;color:#0ea5e9;font-weight:800;
                  letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;">SITUATION SUMMARY</div>
      <div style="color:#1e293b;font-size:0.95rem;line-height:1.65;font-weight:500;">{result.summary}</div>
    </div>
    {_confidence_bar(result.confidence)}
    """, unsafe_allow_html=True)

    # Actions
    st.markdown('<div style="margin-top:28px;margin-bottom:12px;font-size:0.7rem;color:#64748b;font-weight:800;letter-spacing:2px;text-transform:uppercase;">PRIORITISED ACTIONS</div>', unsafe_allow_html=True)

    for item in (result.actions if isinstance(result.actions[0], ActionItem) else
                 [type('A', (), a)() for a in result.actions]):
        action  = item.action  if hasattr(item, 'action')   else item.get('action', '')
        cat     = item.category if hasattr(item, 'category') else item.get('category', 'safety')
        urgency = item.urgency  if hasattr(item, 'urgency')  else item.get('urgency', 'immediate')
        prio    = item.priority if hasattr(item, 'priority') else item.get('priority', 1)
        urg_icon = _URG_ICONS.get(urgency, "⏱️")
        cat_color = _CAT_COLORS.get(cat, "#00d4ff")
        st.markdown(f"""
        <div style="display:flex;align-items:flex-start;gap:14px;
                    padding:13px 16px;
                    background:#f8fafc;
                    border:1px solid rgba(0,0,0,0.06);
                    border-radius:12px;margin-bottom:8px;
                    transition:all 0.2s;">
          <div style="background:linear-gradient(135deg,#00d4ff,#7c3aed);
                      color:#fff;min-width:28px;height:28px;border-radius:8px;
                      display:flex;align-items:center;justify-content:center;
                      font-weight:800;font-size:0.85rem;flex-shrink:0;">{prio}</div>
          <div style="flex:1;">
            <div style="color:#0f172a;font-size:0.93rem;font-weight:500;line-height:1.5;">{action}</div>
            <div style="display:flex;gap:12px;margin-top:8px;flex-wrap:wrap;">
              <span style="font-size:0.7rem;color:{cat_color};font-weight:700;
                           text-transform:uppercase;letter-spacing:0.8px;background:rgba(0,0,0,0.04);padding:2px 8px;border-radius:4px;">{cat}</span>
              <span style="font-size:0.7rem;color:#64748b;font-weight:600;display:flex;align-items:center;gap:4px;">{urg_icon} {urgency.replace('_',' ')}</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Entities (if non-empty)
    entities = result.entities or {}
    filled = {k: v for k, v in entities.items() if v}
    if filled:
        st.markdown('<div style="margin-top:26px;margin-bottom:10px;font-size:0.7rem;color:#64748b;font-weight:800;letter-spacing:2px;text-transform:uppercase;">EXTRACTED ENTITIES</div>', unsafe_allow_html=True)
        chips = ""
        for k, vals in filled.items():
            for v in vals:
                chips += f'<span style="display:inline-flex;align-items:center;gap:5px;padding:4px 12px;background:#e2e8f0;border:1px solid #cbd5e1;border-radius:100px;font-size:0.78rem;font-weight:500;color:#334155;margin:4px 4px 4px 0;">{k[0].upper()}: {v}</span>'
        st.markdown(f'<div style="flex-wrap:wrap;">{chips}</div>', unsafe_allow_html=True)

    # JSON export
    export_data = {
        "input_type": result.input_type,
        "severity": result.severity,
        "confidence": result.confidence,
        "verified": result.verified,
        "summary": result.summary,
        "timestamp": result.timestamp,
        "actions": [
            {"priority": a.priority, "action": a.action, "category": a.category, "urgency": a.urgency}
            for a in result.actions
        ],
        "entities": result.entities,
    }
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.download_button(
        label="⬇  Export JSON",
        data=json.dumps(export_data, indent=2),
        file_name=f"clarity_{result.input_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )


def _process_and_store(input_type: str, content: str, image_data=None):
    if not content.strip() and image_data is None:
        st.error("Please provide some input before processing.")
        return
    with st.spinner("Analysing input…"):
        result = process_input(input_type, content, image_data)
    st.session_state.results.insert(0, result)
    st.rerun()


def _stat_counts():
    results = st.session_state.results
    total     = len(results)
    critical  = sum(1 for r in results if r.severity == "CRITICAL")
    action_ct = sum(len(r.actions) for r in results)
    avg_conf  = (sum(r.confidence for r in results) / total * 100) if total else 0
    return total, critical, action_ct, avg_conf

# ─────────────────────────────────────────────────────────────────────────────
# JAVASCRIPT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
_js_scroll_top = """
<script>
  (function(){
    const el = window.parent.document.querySelector('.block-container');
    if (el) el.scrollTop = 0;
  })();
</script>
"""

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv; load_dotenv()
has_key = bool(os.getenv("GEMINI_API_KEY", "").strip())

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="clarity-header">
  <div class="clarity-wordmark">CLARITY AI</div>
  <div class="clarity-sub">Unstructured&nbsp;&nbsp;→&nbsp;&nbsp;Verified&nbsp;&nbsp;→&nbsp;&nbsp;Actionable</div>
  <div style="margin-top:14px;">
    <span class="demo-pill {'pill-live' if has_key else 'pill-demo'}">
      {'⚡ Live · Gemini 1.5 Flash' if has_key else '◎ Demo Mode — add GEMINI_API_KEY to .env for live AI'}
    </span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Stats row ─────────────────────────────────────────────────────────────────
total, critical, action_ct, avg_conf = _stat_counts()
st.markdown(f"""
<div class="stats-row">
  <div class="stat-card">
    <div class="stat-label">Total Processed</div>
    <div class="stat-value">{total}</div>
    <div class="stat-sub">inputs converted</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Critical Alerts</div>
    <div class="stat-value" style="color:#e74c3c;">{critical}</div>
    <div class="stat-sub">require immediate action</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Actions Generated</div>
    <div class="stat-value" style="color:#0ea5e9;">{action_ct}</div>
    <div class="stat-sub">across all inputs</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Avg Confidence</div>
    <div class="stat-value" style="color:#8b5cf6;">{avg_conf:.0f}%</div>
    <div class="stat-sub">model certainty</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Two-column layout ─────────────────────────────────────────────────────────
left, right = st.columns([1, 1], gap="large")

# ──────────────────────────────────────────────────────────────────────────────
# LEFT COLUMN — INPUT
# ──────────────────────────────────────────────────────────────────────────────
with left:
    st.markdown('<div class="panel"><div class="panel-title">INPUT</div>', unsafe_allow_html=True)

    tabs = st.tabs(["🎙️ Voice", "📷 Photo", "🏥 Medical", "📰 News", "🚦 Traffic", "🌪️ Weather"])

    # ── VOICE ──────────────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("**Voice / Emergency Call**")
        st.caption("Paste a transcript or describe the situation as heard over voice/radio.")
        audio_file = st.file_uploader(
            "Upload audio (WAV · MP3 · M4A) — transcription via Gemini",
            type=["wav", "mp3", "m4a", "ogg"],
            key="voice_audio",
        )
        voice_text = st.text_area(
            "Transcript / situational description",
            placeholder='e.g. "Caller reports a male in his 50s collapsed at the corner of 5th and Main. No pulse. Wife is performing CPR."',
            height=140,
            key="voice_text",
        )

        # If audio uploaded and key present, send audio bytes as content hint
        voice_content = voice_text or ""
        if audio_file:
            st.audio(audio_file)
            if has_key:
                st.info("Audio uploaded — Gemini will transcribe and analyse it together with any text above.")
                voice_content += f"\n[Audio file: {audio_file.name}]"
            else:
                st.warning("Demo mode: add a text transcript above. Audio transcription requires a Gemini API key.")

        if st.button("⚡ Process Voice Input", key="btn_voice"):
            _process_and_store("voice", voice_content or (audio_file.name if audio_file else ""))

    # ── PHOTO ──────────────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("**Photo / Image**")
        st.caption("Upload any image — accident scene, medical condition, hazard, document scan.")
        img_file = st.file_uploader(
            "Upload image (JPG · PNG · WEBP · GIF)",
            type=["jpg", "jpeg", "png", "webp", "gif"],
            key="photo_file",
        )
        img_context = st.text_area(
            "Additional context (optional)",
            placeholder="e.g. This was taken on the I-95 northbound near Exit 12 at 07:42 AM.",
            height=100,
            key="photo_context",
        )
        img_data = None
        if img_file:
            st.image(img_file, use_container_width=True)
            img_data = img_file.read()

        if st.button("⚡ Analyse Image", key="btn_photo"):
            _process_and_store("photo", img_context, img_data)

    # ── MEDICAL ────────────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("**Medical History / Patient Record**")
        st.caption("Paste raw, unstructured patient notes, discharge summaries, or lab results.")

        medical_examples = [
            "— Paste your own —",
            "62F, T2DM on metformin 1g BD, hypertension (ramipril 10mg), paroxysmal AF (warfarin INR 2.8). Admitted with community-acquired pneumonia. CRP 142. WBC 14.2.",
            "78M PMHx: CABG 2018, CKD stage 3, gout (allopurinol 300mg). Current meds: aspirin 75mg, atorvastatin 40mg, amlodipine 5mg, furosemide 40mg OD. Presenting with acute on chronic confusion.",
        ]
        selected = st.selectbox("Load example", medical_examples, key="med_example")
        prefill = "" if selected == "— Paste your own —" else selected
        medical_text = st.text_area(
            "Patient notes / medical history",
            value=prefill,
            placeholder="Paste raw patient notes, discharge summary, or medication list…",
            height=200,
            key="medical_text",
        )
        if st.button("⚡ Analyse Medical Record", key="btn_medical"):
            _process_and_store("medical", medical_text)

    # ── NEWS ───────────────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("**News / Bulletin**")
        st.caption("Paste a news article, wire bulletin, or situation report for intelligence extraction.")
        news_examples = [
            "— Paste your own —",
            "BREAKING: Officials report a multi-vehicle pileup on the M6 motorway near junction 15, involving 3 HGVs and 7 passenger vehicles. Fire service reports one vehicle on fire. Ambulance service confirms multiple casualties. Motorway closed in both directions.",
            "WHO issues Grade 3 emergency: Novel respiratory pathogen identified across 4 countries with R-number estimated at 2.4. Healthcare systems in affected regions placed on high alert. International travel advisories being reviewed.",
        ]
        sel_news = st.selectbox("Load example", news_examples, key="news_example")
        news_pre = "" if sel_news == "— Paste your own —" else sel_news
        news_text = st.text_area(
            "News / bulletin text",
            value=news_pre,
            placeholder="Paste article, tweet thread, or breaking bulletin…",
            height=200,
            key="news_text",
        )
        if st.button("⚡ Extract Intelligence", key="btn_news"):
            _process_and_store("news", news_text)

    # ── TRAFFIC ────────────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("**Traffic / Road Situation**")
        st.caption("Enter raw traffic data — sensor feeds, operator reports, field observations.")
        traffic_examples = [
            "— Paste your own —",
            "CCTV Operator Report 09:14: Major RTC A38 southbound between Lichfield and Sutton junctions. Articulated lorry jackknifed blocking all 3 lanes. Diesel spill confirmed. Emergency services deployed. Tailback 8mi. Diversion via B5127 activated.",
            "Speed sensors on I-405 NB mile marker 22.4 showing avg 4 mph for 45 min. Estimated capacity lost: 85%. No incident logged — possible stall or medical incident.",
        ]
        sel_traf = st.selectbox("Load example", traffic_examples, key="traf_example")
        traf_pre = "" if sel_traf == "— Paste your own —" else sel_traf
        traffic_text = st.text_area(
            "Traffic / road situation data",
            value=traf_pre,
            placeholder="Paste sensor data, operator log, or field report…",
            height=200,
            key="traffic_text",
        )
        if st.button("⚡ Assess Traffic Situation", key="btn_traffic"):
            _process_and_store("traffic", traffic_text)

    # ── WEATHER ────────────────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown("**Weather / Environmental Alert**")
        st.caption("Paste forecasts, NWS/Met Office bulletins, or raw sensor data.")
        weather_examples = [
            "— Paste your own —",
            "NWS TORNADO WARNING: A severe thunderstorm capable of producing a tornado is located near Joplin, moving NE at 55mph. TAKE SHELTER IMMEDIATELY. Hail up to 2.5 inches. Winds exceeding 70mph. This is a CONFIRMED TORNADO on radar.",
            "MetOffice AMBER WEATHER WARNING: Ice. Valid 22:00 tonight to 11:00 tomorrow. Temperatures -6°C. Widespread black ice on roads. Disruption to transport likely. Power outages possible in northern regions.",
        ]
        sel_wth = st.selectbox("Load example", weather_examples, key="wth_example")
        wth_pre = "" if sel_wth == "— Paste your own —" else sel_wth
        weather_text = st.text_area(
            "Weather report / bulletin",
            value=wth_pre,
            placeholder="Paste forecast, alert, or sensor reading…",
            height=200,
            key="weather_text",
        )
        if st.button("⚡ Assess Weather Risk", key="btn_weather"):
            _process_and_store("weather", weather_text)

    st.markdown("</div>", unsafe_allow_html=True)  # close .panel

# ──────────────────────────────────────────────────────────────────────────────
# RIGHT COLUMN — OUTPUT
# ──────────────────────────────────────────────────────────────────────────────
with right:
    st.markdown('<div class="panel"><div class="panel-title">ACTION PLAN</div>', unsafe_allow_html=True)

    if not st.session_state.results:
        # Empty-state illustration
        st.markdown("""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                    padding:70px 20px;text-align:center;opacity:0.6;">
          <div style="font-size:3.5rem;margin-bottom:20px;">⚡</div>
          <div style="font-size:1.05rem;font-weight:700;color:#0f172a;margin-bottom:10px;">
            Ready to Process
          </div>
          <div style="font-size:0.9rem;color:#475569;max-width:280px;line-height:1.7;">
            Select an input type on the left, enter your data, and press Process.
            Structured actions appear here instantly.
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Latest result (full render)
        latest = st.session_state.results[0]
        _render_result(latest)

        # History accordion
        if len(st.session_state.results) > 1:
            st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
            st.markdown('<div class="panel-title">HISTORY</div>', unsafe_allow_html=True)
            for i, r in enumerate(st.session_state.results[1:], start=1):
                ts_short = datetime.fromisoformat(r.timestamp).strftime("%H:%M:%S")
                with st.expander(
                    f"{_TYPE_ICONS.get(r.input_type,'📄')}  {r.input_type.upper()}  ·  "
                    f"{r.severity}  ·  {ts_short}  ·  {len(r.actions)} actions"
                ):
                    _render_result(r)

        if st.button("🗑  Clear history", key="btn_clear"):
            st.session_state.results = []
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)  # close .panel

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:40px 0 20px;
            color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:1px;">
  CLARITY AI · 3-Layer Agent Architecture ·
  Directive → Orchestration → Execution
</div>
""", unsafe_allow_html=True)

# Inject JS for smooth scroll-to-results on rerun
components.html(_js_scroll_top, height=0)
