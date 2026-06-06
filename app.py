from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import gradio as gr
import pandas as pd

from formpilot.engine import analyze_form, export_trace, rows_to_csv
from formpilot.model_assist import DEFAULT_SMALL_MODEL, try_hf_model_assist


APP_DIR = Path(__file__).resolve().parent
TRACE_DIR = APP_DIR / "traces"
EXPORT_DIR = APP_DIR / "exports"
TRACE_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

SAMPLE_FORM = """Community Center Membership Form

Full name: ____________________
Email: ____________________
Phone: ____________________
Address: ____________________
Emergency contact: ____________________
Relationship: ____________________
Signature: ____________________
Date: ____________________
"""

SAMPLE_FACTS = """Full name: Jordan Lee
Email: jordan.lee@example.com
Phone: 555-0137
Address: 42 Maple Street, Springfield, NY 10027
Emergency contact: Priya Lee
Relationship: Sister
Date: June 6, 2026
"""

CSS = """
.gradio-container {
  max-width: 1240px !important;
}
#hero {
  padding: 8px 0 16px 0;
  border-bottom: 1px solid #d7dde5;
}
#hero h1 {
  font-size: 34px;
  line-height: 1.05;
  letter-spacing: 0;
  margin: 0 0 8px 0;
}
#hero p {
  color: #5b6470;
  max-width: 860px;
  font-size: 15px;
}
.status-ready {
  color: #1f6f4a;
  font-weight: 700;
}
.status-review {
  color: #9a6500;
  font-weight: 700;
}
.status-missing {
  color: #a33d3d;
  font-weight: 700;
}
.panel-note {
  border: 1px solid #d7dde5;
  border-radius: 8px;
  background: #ffffff;
  padding: 12px 14px;
}
"""


def _status_html(rows: list[dict[str, Any]], risks: list[str]) -> str:
    ready = sum(1 for row in rows if row["status"] == "ready")
    review = sum(1 for row in rows if row["status"] == "review")
    missing = sum(1 for row in rows if row["status"] == "missing")
    risk_items = "".join(f"<li>{risk}</li>" for risk in risks)
    return f"""
<div class="panel-note">
  <p><span class="status-ready">{ready} ready</span> · <span class="status-review">{review} review</span> · <span class="status-missing">{missing} missing</span></p>
  <ul>{risk_items}</ul>
</div>
"""


def _write_export_files(payload: dict[str, Any]) -> tuple[str, str]:
    trace_path = export_trace(payload, TRACE_DIR)
    csv_path = EXPORT_DIR / "formpilot_latest_fields.csv"
    csv_path.write_text(rows_to_csv(payload["rows"]), encoding="utf-8")
    return trace_path, str(csv_path)


def _model_payload_to_rows(model_payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = model_payload.get("fields", [])
    normalized = []
    for row in rows:
        normalized.append(
            {
                "field": str(row.get("field", "")),
                "proposed_value": str(row.get("proposed_value", "")),
                "status": str(row.get("status", "review")),
                "confidence": int(row.get("confidence", 0) or 0),
                "source": str(row.get("source", "")),
                "note": str(row.get("note", "")),
            }
        )
    return normalized


def run_pilot(
    form_text: str,
    user_facts: str,
    mode: str,
    model_id: str,
) -> tuple[pd.DataFrame, str, str, str, dict[str, Any], str, str]:
    if not form_text.strip():
        raise gr.Error("Paste a form or request first.")

    payload = analyze_form(form_text, user_facts)
    backend_note = "Local structured matcher"

    if mode == "Small model assist":
        try:
            model_payload = try_hf_model_assist(form_text, user_facts, model_id.strip() or DEFAULT_SMALL_MODEL)
            model_rows = _model_payload_to_rows(model_payload)
            if model_rows:
                payload["rows"] = model_rows
                payload["questions"] = model_payload.get("questions", payload["questions"])
                payload["risk_summary"] = model_payload.get("risk_summary", payload["risk_summary"])
                payload["copy_ready"] = "\n".join(
                    f"{row['field']}: {row['proposed_value'] or '[NEEDS USER INPUT]'}"
                    for row in model_rows
                )
                backend_note = f"Small model assist: {model_id.strip() or DEFAULT_SMALL_MODEL}"
        except Exception as exc:
            payload["risk_summary"].insert(
                0,
                f"Small model assist failed; used local matcher instead. Reason: {exc}",
            )

    payload["backend"] = backend_note
    trace_path, csv_path = _write_export_files(payload)

    rows = payload["rows"]
    table = pd.DataFrame(rows, columns=["field", "proposed_value", "status", "confidence", "source", "note"])
    questions = "\n".join(f"- {question}" for question in payload["questions"]) or "No missing-field questions detected."
    summary = _status_html(rows, payload["risk_summary"])
    return table, payload["copy_ready"], questions, summary, payload, trace_path, csv_path


def clear_outputs() -> tuple[pd.DataFrame, str, str, str, dict[str, Any], None, None]:
    return pd.DataFrame(), "", "", "", {}, None, None


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Offline Form Pilot") as demo:
        gr.Markdown(
            """
# Offline Form Pilot
Paste a form and the facts you are willing to use. The app prepares a review table, missing-field questions, and copy-ready text without submitting anything.
""",
            elem_id="hero",
        )

        with gr.Row():
            with gr.Column(scale=5):
                form_text = gr.Textbox(
                    label="Form or request text",
                    value=SAMPLE_FORM,
                    lines=12,
                    max_lines=18,
                )
                user_facts = gr.Textbox(
                    label="User facts",
                    value=SAMPLE_FACTS,
                    lines=10,
                    max_lines=16,
                )
            with gr.Column(scale=3):
                mode = gr.Radio(
                    label="Analysis mode",
                    choices=["Local structured matcher", "Small model assist"],
                    value="Local structured matcher",
                )
                model_id = gr.Textbox(label="Small model id", value=DEFAULT_SMALL_MODEL)
                run_btn = gr.Button("Prepare form review", variant="primary")
                clear_btn = gr.Button("Clear outputs")
                gr.Markdown(
                    """
Human review is required. Do not paste secrets unless you are comfortable with the selected backend.
""",
                    elem_classes=["panel-note"],
                )

        summary = gr.HTML()
        table = gr.Dataframe(
            label="Review table",
            headers=["field", "proposed_value", "status", "confidence", "source", "note"],
            wrap=True,
            interactive=False,
        )
        with gr.Row():
            copy_ready = gr.Textbox(label="Copy-ready draft", lines=10, buttons=["copy"])
            questions = gr.Textbox(label="Questions before copying", lines=10, buttons=["copy"])
        with gr.Accordion("Trace and exports", open=False):
            raw_json = gr.JSON(label="Trace JSON")
            trace_file = gr.File(label="Download trace JSON")
            csv_file = gr.File(label="Download field CSV")

        run_btn.click(
            run_pilot,
            inputs=[form_text, user_facts, mode, model_id],
            outputs=[table, copy_ready, questions, summary, raw_json, trace_file, csv_file],
            api_name="prepare_form_review",
        )
        clear_btn.click(
            clear_outputs,
            outputs=[table, copy_ready, questions, summary, raw_json, trace_file, csv_file],
        )

    return demo


demo = build_demo()


if __name__ == "__main__":
    demo.launch(css=CSS)
