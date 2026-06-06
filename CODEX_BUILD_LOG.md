# Codex Build Log

This project is being built with OpenAI Codex as the coding agent for the Build Small Hackathon OpenAI/Codex track.

## Build Principles

- Keep commits small and Codex-attributed.
- Keep the app review-first: never auto-submit forms.
- Make model behavior inspectable through structured outputs and traces.
- Prefer a small-model-friendly workflow over a generic chatbot.

## Timeline

### 2026-06-06

- User selected the form-filling concept.
- Codex initialized a fresh standalone project under `projects/offline-form-pilot`.
- Codex added the initial README, build log, requirements, and git hygiene files.

## Planned Codex Milestones

1. Scaffold repo and README.
2. Implement Gradio app and deterministic field matcher.
3. Add optional small-model backends and trace export.
4. Add tests and local verification.
5. Push public GitHub repo with Codex-attributed commits.
6. Deploy Hugging Face Space after HF auth is available.
