# Local Video Factory (Windows-first)

## Product direction
Run the production engine on the owner's PC. Cloud services are optional, not required for rendering. The PC is the factory: local API, local job queue, FFmpeg, generated assets, and MP4 archive.

## Target workflow
1. Open the factory launcher.
2. Enter topic, language, duration, visual style, voice, output ratio and platforms.
3. Review script and storyboard before render.
4. Queue one render at a time by default; show stage, elapsed time, logs and cancel/retry.
5. Validate output with ffprobe before marking complete.
6. Open output folder or preview MP4; publishing is a separate explicit action.

## Architecture
- Desktop browser UI at http://127.0.0.1:8000 (loopback only).
- FastAPI local service; no public bind by default.
- SQLite job ledger with queued/running/completed/failed states.
- Worker subprocess for FFmpeg so render crashes do not kill the UI/API.
- Per-job workspace: output/jobs/<job-id>/ with script, prompts, images, audio, logs, QA report and final MP4.
- Local media archive; cloud upload/publishing adapters remain optional.
- AI providers are optional remote APIs. If unavailable, local deterministic templates/assets should report degraded mode rather than pretend AI succeeded.

## Reliability requirements
- Do not run heavy model inference inside the UI/API process.
- Use bounded queue/concurrency (default 1), disk-space preflight, subprocess timeout and cancellation.
- Persist every stage transition; on restart recover queued jobs and mark interrupted jobs recoverable/failed with clear reason.
- Never store API keys in source control or expose them to browser responses.
- Bind to 127.0.0.1 by default; require explicit opt-in and authentication before LAN access.
- Validate MP4 duration and video/audio streams with ffprobe. Failed QA must block publish.
- Publishing requires an explicit user click and per-platform credentials; never auto-publish by default.

## Windows setup (initial)
1. Install Python 3.11+ and FFmpeg; verify `python --version` and `ffmpeg -version`.
2. Clone this repository and open its folder in PowerShell.
3. Create venv: `py -3.11 -m venv .venv`; activate: `.\.venv\Scripts\Activate.ps1`.
4. Install dependencies: `python -m pip install -r requirements.txt`.
5. Copy `.env.example` to `.env`; add only provider keys the owner chooses to use.
6. Start API with `python -m uvicorn api:app --host 127.0.0.1 --port 8000`.
7. Open `http://127.0.0.1:8000/docs` for API smoke test. The production desktop dashboard is a separate UI milestone.

## Delivery gates
- G1: clean install and /health on Windows.
- G2: one sample topic completes end-to-end and produces a playable MP4.
- G3: restart during render does not corrupt other jobs; status is understandable.
- G4: queue, logs, output library and QA are visible in UI.
- G5: optional publishing tested separately with user-owned credentials.
- G6: package as a one-click Windows launcher only after G1-G5 pass.

## Current status
This document defines the migration target. It is not evidence that the PC has been configured or that a local render has passed. Keep Render/Oracle path available until local acceptance tests pass; do not delete working artifacts or secrets.
