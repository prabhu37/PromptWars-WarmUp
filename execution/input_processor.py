"""
execution/input_processor.py
────────────────────────────
Execution Layer — Deterministic Processing Engine
Accepts any unstructured input (voice transcript, image, medical text,
news, traffic, weather) and returns a fully structured, prioritised
ActionPlan via Google Gemini.

Falls back to smart keyword-based demo mode when no API key is configured.
"""

import os
import io
import re
import json
import base64
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv
from PIL import Image

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# ── Gemini client (only initialised when key is present) ─────────────────────
_gemini_model = None

def _get_model():
    global _gemini_model
    if _gemini_model is None and GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    return _gemini_model


# ── Data classes ─────────────────────────────────────────────────────────────
@dataclass
class ActionItem:
    priority: int
    action: str
    category: str      # medical | safety | logistics | communication | infrastructure
    urgency: str       # immediate | short_term | long_term


@dataclass
class ProcessedOutput:
    input_type: str
    summary: str
    severity: str      # CRITICAL | HIGH | MEDIUM | LOW
    confidence: float  # 0.0 – 1.0
    actions: list
    entities: dict
    verified: bool
    timestamp: str
    raw_text: str
    metadata: dict = field(default_factory=dict)
    mode: str = "demo"  # "live" | "demo"


# ── Public entry point ────────────────────────────────────────────────────────
def process_input(
    input_type: str,
    content: str = "",
    image_data: Optional[bytes] = None,
) -> ProcessedOutput:
    """
    Route any input to the correct handler.
    Uses Gemini if API key is set; otherwise falls back to demo mode.
    """
    timestamp = datetime.now().isoformat()
    model = _get_model()

    if model:
        return _process_with_gemini(model, input_type, content, image_data, timestamp)
    return _process_demo(input_type, content, image_data, timestamp)


# ── Gemini path ───────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """
You are an emergency response AI. Analyse the provided input and respond with
ONLY a valid JSON object — no markdown fences, no extra text — matching this schema exactly:

{
  "summary": "...",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW",
  "confidence": 0.95,
  "actions": [
    {"priority": 1, "action": "...", "category": "...", "urgency": "immediate | short_term | long_term"}
  ],
  "entities": {
    "people": [], "locations": [], "conditions": [], "medications": [], "dates": []
  },
  "verified": true
}

Rules:
- severity CRITICAL → life-threatening situation requiring immediate intervention
- severity HIGH     → significant risk within hours
- severity MEDIUM   → notable concern within days
- severity LOW      → informational / preventative
- actions must be concrete, specific, and ordered by priority
- verified = true only when you are confident the information is internally consistent
- Provide at least 3 and at most 8 action items
"""

_TYPE_PROMPTS = {
    "voice":    "This is a voice transcript (emergency call / field report). Analyse it:",
    "photo":    "Analyse this image for hazards, medical emergencies, or situations requiring action:",
    "medical":  "This is a medical history / patient record. Identify risks, interactions, and required actions:",
    "news":     "This is a news article or bulletin. Extract key actionable intelligence and risks:",
    "traffic":  "This is a traffic / road situation report. Identify hazards and required response actions:",
    "weather":  "This is a weather report or alert. Identify risks and required safety actions:",
}


def _process_with_gemini(model, input_type, content, image_data, timestamp) -> ProcessedOutput:
    import google.generativeai as genai

    type_prompt = _TYPE_PROMPTS.get(input_type, "Analyse this input:")
    prompt_parts = [_SYSTEM_PROMPT, f"\n\n{type_prompt}\n\n{content}"]

    # Attach image if present
    if image_data:
        img = _resize_image(image_data)
        prompt_parts.append(img)

    try:
        response = model.generate_content(prompt_parts)
        raw_json = response.text.strip()
        # Strip markdown fences if model wraps them anyway
        raw_json = re.sub(r"^```(?:json)?\n?", "", raw_json)
        raw_json = re.sub(r"\n?```$", "", raw_json)
        data = json.loads(raw_json)
    except Exception as e:
        # Self-anneal: fall back to demo and attach error metadata
        result = _process_demo(input_type, content, image_data, timestamp)
        result.metadata["gemini_error"] = str(e)
        return result

    actions = [
        ActionItem(
            priority=a.get("priority", i + 1),
            action=a.get("action", ""),
            category=a.get("category", "safety"),
            urgency=a.get("urgency", "immediate"),
        )
        for i, a in enumerate(data.get("actions", []))
    ]

    return ProcessedOutput(
        input_type=input_type,
        summary=data.get("summary", ""),
        severity=data.get("severity", "MEDIUM"),
        confidence=float(data.get("confidence", 0.85)),
        actions=actions,
        entities=data.get("entities", _empty_entities()),
        verified=data.get("verified", False),
        timestamp=timestamp,
        raw_text=content,
        mode="live",
    )


def _resize_image(image_data: bytes) -> "Image.Image":
    """Resize image to max 2048px on either axis before sending to model."""
    img = Image.open(io.BytesIO(image_data))
    img.thumbnail((2048, 2048), Image.LANCZOS)
    return img


# ── Demo / fallback path ──────────────────────────────────────────────────────
_KEYWORD_MAP = {
    "CRITICAL": {
        "voice":   ["cardiac arrest", "heart attack", "stroke", "not breathing",
                    "unconscious", "severe bleeding", "anaphylaxis", "drowning",
                    "explosion", "shooting", "fire", "trapped"],
        "medical": ["cardiac arrest", "anaphylaxis", "sepsis", "multi-organ",
                    "do not resuscitate", "dnr", "allerg", "severe interact"],
        "traffic": ["multiple vehicles", "fatality", "overturned", "hazmat",
                    "bridge collapse", "tunnel", "blocked emergency"],
        "weather": ["tornado", "hurricane category", "earthquake", "tsunami",
                    "flash flood warning", "wildfire evacuation"],
        "news":    ["mass casualty", "terrorism", "nuclear", "outbreak", "pandemic"],
        "photo":   ["fire", "flood", "collapse", "bleeding", "crush", "smoke"],
    },
    "HIGH": {
        "voice":   ["chest pain", "can't breathe", "difficulty breathing", "allergic",
                    "bleeding", "unconscious", "overdose", "suicide"],
        "medical": ["hypertension", "diabetes", "cancer", "chemotherapy",
                    "blood thinner", "warfarin", "insulin", "pacemaker"],
        "traffic": ["accident", "collision", "road closure", "emergency vehicle",
                    "injury", "pile-up", "debris on highway"],
        "weather": ["severe thunderstorm", "blizzard", "ice storm", "tropical storm",
                    "high wind", "flood watch", "winter storm"],
        "news":    ["breaking", "evacuation", "recall", "contamination", "chemical"],
        "photo":   ["crash", "injury", "hazard", "spill", "structural damage"],
    },
    "MEDIUM": {
        "voice":   ["pain", "fever", "dizzy", "nausea", "vomiting", "cough",
                    "delay", "waiting", "no ambulance"],
        "medical": ["medication", "prescription", "surgery", "chronic", "history of",
                    "elevated", "mild", "controlled"],
        "traffic": ["congestion", "slow traffic", "construction", "pothole",
                    "minor accident", "breakdown"],
        "weather": ["rain", "snow", "wind advisory", "fog", "heat advisory",
                    "thunderstorm watch"],
        "news":    ["warning", "investigation", "concern", "risk", "advisory"],
        "photo":   ["wet floor", "warning sign", "crowd", "construction"],
    },
}

_DEMO_TEMPLATES = {
    "voice": {
        "CRITICAL": {
            "summary": "Emergency call indicates a life-threatening situation. Patient is unresponsive with signs of cardiac arrest. Immediate ALS response required.",
            "actions": [
                ActionItem(1, "Dispatch Advanced Life Support unit immediately", "safety", "immediate"),
                ActionItem(2, "Instruct caller to begin CPR (30 compressions : 2 breaths)", "medical", "immediate"),
                ActionItem(3, "Activate nearest AED location and dispatch trained bystander", "medical", "immediate"),
                ActionItem(4, "Notify receiving emergency department of incoming critical patient", "communication", "immediate"),
                ActionItem(5, "Dispatch police for traffic clearance on route", "logistics", "immediate"),
                ActionItem(6, "Document caller ID and exact GPS coordinates", "logistics", "immediate"),
            ],
            "entities": {"people": ["caller", "patient"], "locations": ["reported address"], "conditions": ["cardiac arrest"], "medications": [], "dates": [datetime.now().strftime("%Y-%m-%d")]},
        },
        "HIGH": {
            "summary": "Voice report indicates a significant medical or safety emergency. Situation is serious but patient is conscious. Priority dispatch required.",
            "actions": [
                ActionItem(1, "Dispatch emergency medical services to reported location", "safety", "immediate"),
                ActionItem(2, "Keep caller on line; collect precise location and symptoms", "communication", "immediate"),
                ActionItem(3, "Begin remote triage protocol — assess ABC (Airway, Breathing, Circulation)", "medical", "immediate"),
                ActionItem(4, "Alert nearest hospital emergency department", "medical", "short_term"),
                ActionItem(5, "Log incident in dispatch system with priority flag", "logistics", "short_term"),
            ],
            "entities": {"people": ["caller"], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "MEDIUM": {
            "summary": "Voice report describes a non-critical situation requiring monitoring and response. No immediate life threat detected.",
            "actions": [
                ActionItem(1, "Schedule non-emergency medical transport if required", "logistics", "short_term"),
                ActionItem(2, "Document reported symptoms and relay to duty nurse", "medical", "short_term"),
                ActionItem(3, "Advise caller on self-management steps while help arrives", "medical", "short_term"),
                ActionItem(4, "Follow up in 30 minutes to reassess status", "communication", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "LOW": {
            "summary": "Voice input describes a routine or informational situation. No urgent intervention required.",
            "actions": [
                ActionItem(1, "Log report and forward to relevant department", "logistics", "long_term"),
                ActionItem(2, "Schedule follow-up appointment if medical concern noted", "medical", "long_term"),
                ActionItem(3, "Provide caller with appropriate helpline or resource", "communication", "long_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
    },
    "medical": {
        "CRITICAL": {
            "summary": "Patient record flags life-threatening conditions or dangerous drug interactions requiring immediate physician review and intervention.",
            "actions": [
                ActionItem(1, "Immediate physician review — do not proceed with treatment without sign-off", "medical", "immediate"),
                ActionItem(2, "Flag critical drug interaction to pharmacy and prescribing doctor", "medical", "immediate"),
                ActionItem(3, "Prepare crash cart and alert ICU of potential transfer", "safety", "immediate"),
                ActionItem(4, "Cancel any elective procedures until stabilised", "medical", "immediate"),
                ActionItem(5, "Contact patient's emergency contact / next of kin", "communication", "immediate"),
                ActionItem(6, "Document all interventions in EMR with timestamp", "logistics", "immediate"),
            ],
            "entities": {"people": ["patient"], "locations": ["hospital"], "conditions": [], "medications": [], "dates": []},
        },
        "HIGH": {
            "summary": "Medical history reveals significant co-morbidities and risk factors that require active management and monitoring.",
            "actions": [
                ActionItem(1, "Flag high-risk conditions to on-call physician", "medical", "immediate"),
                ActionItem(2, "Review all current medications for contraindications", "medical", "immediate"),
                ActionItem(3, "Order relevant baseline labs (CBC, CMP, coagulation panel)", "medical", "short_term"),
                ActionItem(4, "Update care plan to include risk-specific monitoring", "medical", "short_term"),
                ActionItem(5, "Schedule specialist referral (cardiology / endocrinology / oncology)", "medical", "short_term"),
                ActionItem(6, "Educate patient on warning signs requiring emergency contact", "communication", "short_term"),
            ],
            "entities": {"people": ["patient"], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "MEDIUM": {
            "summary": "Medical history indicates chronic conditions under reasonable control. Routine monitoring and preventive care adjustments recommended.",
            "actions": [
                ActionItem(1, "Schedule 3-month follow-up for chronic condition review", "medical", "short_term"),
                ActionItem(2, "Update medication list and reconcile with pharmacy records", "medical", "short_term"),
                ActionItem(3, "Order annual preventive screenings as per guidelines", "medical", "long_term"),
                ActionItem(4, "Provide patient with updated care instructions", "communication", "long_term"),
            ],
            "entities": {"people": ["patient"], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "LOW": {
            "summary": "Medical history appears routine with no significant risk factors identified at this time.",
            "actions": [
                ActionItem(1, "Annual wellness check scheduled", "medical", "long_term"),
                ActionItem(2, "Maintain current medication regimen", "medical", "long_term"),
                ActionItem(3, "Patient education on healthy lifestyle maintained", "communication", "long_term"),
            ],
            "entities": {"people": ["patient"], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
    },
    "traffic": {
        "CRITICAL": {
            "summary": "Major traffic incident detected with multi-vehicle involvement, potential fatalities, and blocked emergency access routes. Immediate multi-agency response required.",
            "actions": [
                ActionItem(1, "Dispatch fire, EMS, and police to incident location immediately", "safety", "immediate"),
                ActionItem(2, "Activate traffic management centre for full corridor closure", "infrastructure", "immediate"),
                ActionItem(3, "Reroute all incoming traffic via designated alternate routes", "logistics", "immediate"),
                ActionItem(4, "Alert hospital emergency department of incoming trauma patients", "medical", "immediate"),
                ActionItem(5, "Deploy hazmat team if fuel/chemical spill is present", "safety", "immediate"),
                ActionItem(6, "Issue Wireless Emergency Alert to affected zone", "communication", "immediate"),
                ActionItem(7, "Coordinate with public transit to add capacity on alternate routes", "logistics", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "HIGH": {
            "summary": "Significant traffic incident or road hazard detected. Emergency services required. Traffic flow disruption expected for 1–3 hours.",
            "actions": [
                ActionItem(1, "dispatch EMS and police to incident site", "safety", "immediate"),
                ActionItem(2, "Implement lane-level signal control to divert traffic", "infrastructure", "immediate"),
                ActionItem(3, "Post dynamic message signs with delay estimates", "communication", "immediate"),
                ActionItem(4, "Notify rideshare and navigation apps of closure", "communication", "short_term"),
                ActionItem(5, "Deploy tow truck and road clearing crews", "logistics", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "MEDIUM": {
            "summary": "Ongoing traffic congestion or minor incident affecting flow. Advisory-level response suitable.",
            "actions": [
                ActionItem(1, "Post advisory on traffic management app", "communication", "short_term"),
                ActionItem(2, "Adjust signal timings on affected corridor", "infrastructure", "short_term"),
                ActionItem(3, "Monitor via CCTV and reassess in 30 minutes", "logistics", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "LOW": {
            "summary": "Minor traffic delay noted. No emergency intervention required.",
            "actions": [
                ActionItem(1, "Update navigation app data with current conditions", "communication", "long_term"),
                ActionItem(2, "Log conditions for quarterly traffic pattern analysis", "logistics", "long_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
    },
    "weather": {
        "CRITICAL": {
            "summary": "Extreme weather event poses immediate threat to life and infrastructure. Mandatory evacuation and emergency shelter activation required.",
            "actions": [
                ActionItem(1, "Issue mandatory evacuation order for Zones A–C immediately", "safety", "immediate"),
                ActionItem(2, "Activate all emergency shelters and coordinate transport for non-mobile residents", "logistics", "immediate"),
                ActionItem(3, "Deploy Emergency Broadcast System alert to all channels", "communication", "immediate"),
                ActionItem(4, "Pre-position search and rescue teams at staging areas", "safety", "immediate"),
                ActionItem(5, "Alert hospitals and care facilities to shelter-in-place protocols", "medical", "immediate"),
                ActionItem(6, "Close all bridges, elevated roads, and coastal roads", "infrastructure", "immediate"),
                ActionItem(7, "Pre-stage utility restoration crews at safe distance", "infrastructure", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "HIGH": {
            "summary": "Severe weather warning in effect. Significant risk to life and property. Proactive protective actions required.",
            "actions": [
                ActionItem(1, "Issue public weather warning via SMS and broadcast media", "communication", "immediate"),
                ActionItem(2, "Open voluntary evacuation shelters in affected county", "logistics", "immediate"),
                ActionItem(3, "Pre-position emergency response assets in safe zones", "safety", "immediate"),
                ActionItem(4, "Advise vulnerable populations to seek indoor shelter", "safety", "immediate"),
                ActionItem(5, "Place utility crews on standby for outage response", "infrastructure", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "MEDIUM": {
            "summary": "Moderate weather advisory in effect. Elevated risk but no immediate life threat. Public awareness recommended.",
            "actions": [
                ActionItem(1, "Issue public advisory on local weather channels", "communication", "short_term"),
                ActionItem(2, "Advise residents to delay non-essential travel", "safety", "short_term"),
                ActionItem(3, "Monitor conditions and upgrade to warning if intensity increases", "logistics", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "LOW": {
            "summary": "Routine weather conditions with minor advisory notes. Standard monitoring applies.",
            "actions": [
                ActionItem(1, "Post standard weather advisory on public portals", "communication", "long_term"),
                ActionItem(2, "Ensure routine maintenance crews are briefed on forecast", "logistics", "long_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
    },
    "news": {
        "CRITICAL": {
            "summary": "Breaking news bulletin indicates a mass-casualty or national-security event. Immediate cross-agency coordination and public communication required.",
            "actions": [
                ActionItem(1, "Activate Emergency Operations Centre (EOC) immediately", "safety", "immediate"),
                ActionItem(2, "Issue verified public safety alert — avoid speculation", "communication", "immediate"),
                ActionItem(3, "Deploy rapid response teams to reported location", "logistics", "immediate"),
                ActionItem(4, "Establish unified command with law enforcement, health, and EOC", "logistics", "immediate"),
                ActionItem(5, "Coordinate with national agencies (FBI / DHS / CDC as applicable)", "communication", "immediate"),
                ActionItem(6, "Suppress unverified social-media amplification via platform liaisons", "communication", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "HIGH": {
            "summary": "High-priority news event requiring coordinated public safety response and proactive communication.",
            "actions": [
                ActionItem(1, "Cross-reference with two additional verified sources before re-broadcasting", "communication", "immediate"),
                ActionItem(2, "Alert relevant agency heads for situational awareness", "communication", "immediate"),
                ActionItem(3, "Prepare public statement with official spokesperson", "communication", "short_term"),
                ActionItem(4, "Monitor social media for evolving details and misinformation", "communication", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "MEDIUM": {
            "summary": "News item of moderate significance. Fact-checking and structured stakeholder communication recommended.",
            "actions": [
                ActionItem(1, "Verify claims with primary sources before acting", "communication", "short_term"),
                ActionItem(2, "Brief relevant department heads on potential impact", "communication", "short_term"),
                ActionItem(3, "Prepare holding statement for public enquiries", "communication", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "LOW": {
            "summary": "Informational news item. No immediate action required. File for situational awareness.",
            "actions": [
                ActionItem(1, "Log entry in intelligence bulletin", "logistics", "long_term"),
                ActionItem(2, "Share with relevant stakeholders on next briefing cycle", "communication", "long_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
    },
    "photo": {
        "CRITICAL": {
            "summary": "Image analysis indicates a critical emergency scene — structural collapse, fire, or severe medical emergency visible. Immediate field response required.",
            "actions": [
                ActionItem(1, "Dispatch fire, rescue, and EMS to photographed location", "safety", "immediate"),
                ActionItem(2, "Geolocate image metadata to confirm coordinates", "logistics", "immediate"),
                ActionItem(3, "Establish safety perimeter of at least 100 metres", "safety", "immediate"),
                ActionItem(4, "Alert structural engineering team if collapse suspected", "infrastructure", "immediate"),
                ActionItem(5, "Document and preserve image as official incident evidence", "logistics", "immediate"),
                ActionItem(6, "Begin primary search-and-rescue sweep of visible area", "safety", "immediate"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "HIGH": {
            "summary": "Image shows a significant hazard or safety concern requiring prompt field response.",
            "actions": [
                ActionItem(1, "Dispatch appropriate emergency response team", "safety", "immediate"),
                ActionItem(2, "Identify and isolate hazard source if visible in image", "safety", "immediate"),
                ActionItem(3, "Preserve image chain-of-custody for incident report", "logistics", "short_term"),
                ActionItem(4, "Notify site manager / building owner if property-related", "communication", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "MEDIUM": {
            "summary": "Image indicates a moderate safety concern or maintenance issue requiring attention.",
            "actions": [
                ActionItem(1, "Assign maintenance or safety officer for site inspection", "safety", "short_term"),
                ActionItem(2, "Document hazard in facilities management system", "logistics", "short_term"),
                ActionItem(3, "Place appropriate warning signage at location", "infrastructure", "short_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
        "LOW": {
            "summary": "Image analysis indicates a routine or low-risk scene. No immediate action required.",
            "actions": [
                ActionItem(1, "Log image in situational awareness database", "logistics", "long_term"),
                ActionItem(2, "Include in next routine inspection report", "logistics", "long_term"),
            ],
            "entities": {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []},
        },
    },
}

_CONFIDENCE_MAP = {"CRITICAL": 0.92, "HIGH": 0.83, "MEDIUM": 0.74, "LOW": 0.65}


def _score_severity(input_type: str, text: str) -> str:
    """Simple keyword-scoring for demo mode."""
    text_lower = text.lower()
    for level in ("CRITICAL", "HIGH", "MEDIUM"):
        keywords = _KEYWORD_MAP.get(level, {}).get(input_type, [])
        if any(kw in text_lower for kw in keywords):
            return level
    return "LOW"


def _empty_entities():
    return {"people": [], "locations": [], "conditions": [], "medications": [], "dates": []}


def _process_demo(input_type, content, image_data, timestamp) -> ProcessedOutput:
    """Keyword-based fallback that returns realistic structured output."""
    severity = _score_severity(input_type, content or "")

    # For photo with no descriptive text, default to HIGH so the demo is useful
    if input_type == "photo" and not content and image_data:
        severity = "HIGH"

    template = _DEMO_TEMPLATES.get(input_type, _DEMO_TEMPLATES["news"])[severity]

    return ProcessedOutput(
        input_type=input_type,
        summary=template["summary"],
        severity=severity,
        confidence=_CONFIDENCE_MAP[severity],
        actions=template["actions"],
        entities=template.get("entities", _empty_entities()),
        verified=(severity in ("CRITICAL", "HIGH")),
        timestamp=timestamp,
        raw_text=content or "(image input)",
        metadata={"demo_mode": True},
        mode="demo",
    )
