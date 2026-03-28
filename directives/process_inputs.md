# Directive: Process Unstructured Inputs

## Goal
Transform any messy, unstructured real-world input (voice transcript, image, medical history,
news text, traffic data, weather data) into a structured, prioritised, actionable output.

## Inputs
| Field        | Type              | Required |
|-------------|-------------------|----------|
| input_type  | str (enum)        | ✅        |
| content     | str               | depends  |
| image_data  | bytes (JPEG/PNG)  | only for photo tab |
| audio_data  | bytes (WAV/MP3)   | only for voice tab |

Allowed input_type values: `voice`, `photo`, `medical`, `news`, `traffic`, `weather`

## Tools / Scripts
- **Primary**: `execution/input_processor.py` → `process_input(input_type, content, image_data, audio_data)`
- Returns: `ProcessedOutput` dataclass (see schema below)

## Output Schema
```json
{
  "input_type": "...",
  "summary": "Plain-language summary of the situation",
  "severity": "CRITICAL | HIGH | MEDIUM | LOW",
  "confidence": 0.0 - 1.0,
  "actions": [
    {
      "priority": 1,
      "action": "Exact action to take",
      "category": "medical | safety | logistics | communication | infrastructure",
      "urgency": "immediate | short_term | long_term"
    }
  ],
  "entities": {
    "people": [], "locations": [], "conditions": [], "medications": [], "dates": []
  },
  "verified": true | false,
  "timestamp": "ISO 8601",
  "raw_text": "The input as transcribed/received",
  "metadata": {}
}
```

## Edge Cases & Learnings
- **No OpenAI key**: Falls back to keyword-based demo mode. Notify user via UI banner.
- **Voice with no audio**: Fall back to text input field; do not crash.
- **Image too large**: Resize to max 2048px before encoding to base64.
- **API rate limit (429)**: Catch and surface friendly message; do not retry automatically.
- **Empty input**: Validate before processing; show inline error, do not submit.
- **Ambiguous severity**: Default to higher severity when in doubt (safety-first principle).

## Self-Annealing Notes
_Update this section when new edge cases are discovered._
- 2026-03-28: Initial directive created. Demo mode uses keyword scoring for severity.
