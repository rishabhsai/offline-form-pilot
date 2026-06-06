# Deployment

## GitHub

Public repo:

https://github.com/rishabhsai/offline-form-pilot

The commit history uses Codex-attributed commit messages for the OpenAI/Codex track.

## Hugging Face Space

The local `hf` CLI is installed in the project venv. Authenticate first:

```bash
source .venv/bin/activate
hf auth login
```

If late org access is approved:

```bash
hf repos create build-small-hackathon/offline-form-pilot --type space --space-sdk gradio --exist-ok
hf upload build-small-hackathon/offline-form-pilot . --type space \
  --exclude ".venv/*" \
  --exclude "traces/*" \
  --exclude "exports/*" \
  --commit-message "Codex: upload Offline Form Pilot Space"
```

If org access is not available, use a personal Space:

```bash
hf repos create rishabhsai/offline-form-pilot --type space --space-sdk gradio --exist-ok
hf upload rishabhsai/offline-form-pilot . --type space \
  --exclude ".venv/*" \
  --exclude "traces/*" \
  --exclude "exports/*" \
  --commit-message "Codex: upload Offline Form Pilot Space"
```

After deployment, update `README.md` with the Space URL and push one final Codex-attributed commit to GitHub.

## Space Secrets

For the optional small-model assist mode, add one of these secrets in the Space settings:

- `HF_TOKEN`
- `HUGGINGFACEHUB_API_TOKEN`

The app still runs without a token using the local structured matcher.

## Demo Checklist

1. Paste a messy form.
2. Paste safe sample facts.
3. Run local structured matcher.
4. Switch to small-model assist if the Space token is configured.
5. Show ready/review/missing fields.
6. Show generated questions before copying.
7. Download trace JSON and field CSV.
