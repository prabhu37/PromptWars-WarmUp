# Directives

SOPs (Standard Operating Procedures) written in Markdown.

Each directive defines:
- **Goal** – what the directive accomplishes
- **Inputs** – what data / context is required
- **Tools / Scripts** – which `execution/` scripts to call and with what arguments
- **Outputs** – what deliverables are produced (usually a cloud link)
- **Edge Cases** – known failure modes and how to handle them

## Naming convention

`<verb>_<noun>.md` — e.g. `scrape_website.md`, `generate_report.md`

## Notes

- Directives are living documents. Update them when you learn something new (API limits, timing, better approaches).
- Never delete a directive without explicit user approval.
- Intermediates go in `.tmp/`; final deliverables go to Google Sheets / Slides / etc.
