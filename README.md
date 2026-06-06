---
title: Offline Form Pilot
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.16.0
app_file: app.py
pinned: false
license: mit
short_description: Local-first assistant for turning confusing forms into reviewable fields.
---

# Offline Form Pilot

Offline Form Pilot helps a real person fill confusing forms without handing control to an autopilot. Paste a form, paste the facts you are comfortable using, and the app produces a review table with proposed values, confidence, missing fields, and questions to ask before anything is copied.

The app is designed for the Build Small Hackathon:

- **Track:** Backyard AI.
- **Small model constraint:** default target is a <=4B small model.
- **Safety posture:** no automatic submission, no hidden form filling, no legal/financial certainty.
- **Codex track:** this public repo was built with Codex-attributed commits and includes `CODEX_BUILD_LOG.md`.

## Why Small Models Fit

Form help is mostly narrow extraction, matching, and clarification. A small model can do useful work when the interface forces structured fields, review, and missing-information checks.

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Submission Checklist

- Public GitHub repo linked from this README.
- Hugging Face Space link added after deployment.
- Short demo video.
- Social post.
- Field notes.
- Optional trace dataset with anonymized examples.

## Repository Links

- GitHub: https://github.com/rishabhsai/offline-form-pilot
- Hugging Face Space: pending.
