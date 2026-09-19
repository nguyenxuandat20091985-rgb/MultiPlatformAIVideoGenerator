#!/usr/bin/env python3
"""
FastAPI backend for MultiPlatformAIVideoGenerator.
"""
from __future__ import annotations

import asyncio
import gc
import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import requests

from config.settings import settings
from core.video_qa import validate_final_video
from core import (
    generate_script,
    save_script,
    generate_image_prompts,
    generate_images,
    generate_audio,
    generate_captions,
    compose_video,
    add_captions_to_video,
)
from publishers import list_available_publishers, publish_to_platforms

app = FastAPI(
    title="MultiPlatform AI Video Generator API",
    description="Generate vertical short-form videos with AI and publish to YouTube, TikTok, Facebook.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_ROOT = Path(settings.OUTPUT_DIR)
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(OUTPUT_ROOT)), name="media")


def _mark_interrupted_jobs() -> None:
    """Prevent a crashed Render worker from entering an automatic restart loop."""
    for path in sorted(JOB_STATE_ROOT.glob("*.json")):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if job.get("status") == "running":
            job["status"] = "failed"
            job["updated_at"] = _now()
            for step in job.get("steps", []):
                if step.get("status") == "running":
                    step["status"] = "error"
                    step["message"] = (
                        "Render worker restarted during processing. "
                        "The job was stopped safely; start a new job to retry."
                    )
            try:
                path.write_text(
                    json.dumps(job, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )
            except OSError:
                pass


@app.on_event("startup")
async def recover_jobs_after_restart() -> None:
    # Do not immediately restart a job after a worker crash. On small Render
    # instances that can create an infinite crash -> restart -> crash loop.
    _mark_interrupted_jobs()


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=3)
    title: Optional[str] = None
    style: str = "educational"
    target_audience: str = "general"
    cta: str = "Follow for more!"
    tags: List[str] = Field(default_factory=list)
    platforms: List[str] = Field(default_factory=list)
    skip_captions: bool = False
    folder_name: Optional[str] = None


class PublishRequest(BaseModel):
    video_path: str
    title: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    platforms: List[str] = Field(default_factory=list)


class JobStep(BaseModel):
    name: str
    status: str
    message: str = ""


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str
    request: Dict[str, Any]
    steps: List[JobStep]
    progress_percent: int = 0
    video_url: Optional[str] = None
    video_path: Optional[str] = None
    publish_results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


_jobs: Dict[str, Dict[str, Any]] = {}
JOB_STATE_ROOT = OUTPUT_ROOT / "_jobs"
JOB_STATE_ROOT.mkdir(parents=True, exist_ok=True)


def _job_state_path(job_id: str) -> Path:
    return JOB_STATE_ROOT / f"{job_id}.json"


def _notify_worker_callback(job: Dict[str, Any]) -> None:
    callback_url = job.get("_worker_callback_url")
    callback_token = job.get("_worker_callback_token")
    if not callback_url or not callback_token:
        return
    payload = dict(job)
    payload.pop("_worker_callback_url", None)
    payload.pop("_worker_callback_token", None)
    try:
        requests.post(
            callback_url,
            json=payload,
            headers={"X-Worker-Token": callback_token},
            timeout=10,
        )
    except requests.RequestException:
        pass


def _save_job(job: Dict[str, Any]) -> None:
    path = _job_state_path(job["job_id"])
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)
    _notify_worker_callback(job)


def _load_job(job_id: str) -> Optional[Dict[str, Any]]:
    job = _jobs.get(job_id)
    if job is not None:
        return job
    path = _job_state_path(job_id)
    if not path.exists():
        return None
    try:
        job = json.loads(path.read_text(encoding="utf-8"))
        _jobs[job_id] = job
        return job
    except (OSError, ValueError, TypeError):
        return None

PIPELINE_STEPS = [
    "script",
    "image_prompts",
    "images",
    "audio",
    "compose",
    "captions",
    "publish",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_to_response(job: Dict[str, Any]) -> JobResponse:
    steps = [JobStep(**s) for s in job.get("steps", [])]
    done = sum(1 for s in steps if s.status == "done")
    total = max(len(steps), 1)
    pct = int(100 * done / total)
    if job.get("status") == JobStatus.completed:
        pct = 100
    return JobResponse(
        job_id=job["job_id"],
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        request=job.get("request", {}),
        steps=steps,
        progress_percent=pct,
        video_url=job.get("video_url"),
        video_path=job.get("video_path"),
        publish_results=job.get("publish_results"),
        error=job.get("error"),
    )


def _release_memory() -> None:
    """Return reclaimable Python memory to the OS between heavy pipeline stages."""
    gc.collect()
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)
    except (OSError, AttributeError):
        pass


def _set_step(job: Dict[str, Any], name: str, status: str, message: str = "") -> None:
    for s in job["steps"]:
        if s["name"] == name:
            s["status"] = status
            s["message"] = message
            break
    job["updated_at"] = _now()
    _save_job(job)


def _run_pipeline(job_id: str) -> None:
    job = _load_job(job_id)
    if not job:
        return
    req = job["request"]
    try:
        job["status"] = JobStatus.running
        job["updated_at"] = _now()

        folder_name = req.get("folder_name") or f"job_{job_id[:8]}"
        project = OUTPUT_ROOT / folder_name
        project.mkdir(parents=True, exist_ok=True)
        (project / "images").mkdir(exist_ok=True)
        (project / "audio").mkdir(exist_ok=True)
        (project / "captions").mkdir(exist_ok=True)

        script_path = project / "script.json"
        prompts_path = project / "image_prompts.json"
        images_dir = project / "images"
        audio_dir = project / "audio"
        captions_dir = project / "captions"
        video_path = project / "final_video.mp4"
        final_path = project / "final_video_with_captions.mp4"

        _set_step(job, "script", "running", "Generating script…")
        script = generate_script(
            topic=req["topic"],
            style=req.get("style", "educational"),
            target_audience=req.get("target_audience", "general"),
            cta=req.get("cta", "Follow for more!"),
        )
        save_script(script, script_path)
        _set_step(job, "script", "done", "Script ready")

        _set_step(job, "image_prompts", "running")
        generate_image_prompts(script_path, prompts_path)
        _set_step(job, "image_prompts", "done")

        _set_step(job, "images", "running", "Generating images…")
        image_report = generate_images(prompts_path, images_dir)
        if image_report.get("fallback_used"):
            fallback_count = image_report.get("local_fallback", 0)
            _set_step(
                job,
                "images",
                "done",
                f"Images ready; {fallback_count} local fallback frame(s) used because remote image providers were unavailable.",
            )
        else:
            _set_step(job, "images", "done", "Images ready")
        _release_memory()

        _set_step(job, "audio", "running", "Generating audio…")
        audio_path = generate_audio(script_path, audio_dir)
        audio_report = {}
        report_path = audio_dir / "audio_generation_report.json"
        if report_path.exists():
            try:
                audio_report = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                audio_report = {}
        if audio_report.get("fallback_used"):
            _set_step(job, "audio", "done", "Audio fallback used; video will continue without remote TTS.")
        else:
            _set_step(job, "audio", "done")
        _release_memory()

        _set_step(job, "compose", "running", "Composing video…")
        compose_video(images_dir, audio_path, video_path)
        _release_memory()
        out_video = video_path

        if not req.get("skip_captions", False) and not audio_report.get("fallback_used"):
            _set_step(job, "captions", "running", "Captions…")
            captions_path = generate_captions(audio_path, captions_dir)
            add_captions_to_video(video_path, captions_path, final_path)
            out_video = final_path
            _set_step(job, "captions", "done")
        elif audio_report.get("fallback_used"):
            _set_step(job, "captions", "done", "Skipped because local silent audio fallback was used")
        else:
            _set_step(job, "captions", "done", "Skipped")

        _set_step(job, "qa", "running", "Validating final MP4…")
        qa_report = validate_final_video(out_video)
        job["video_qa"] = qa_report
        _set_step(job, "qa", "done", "Video validated successfully")
        _release_memory()

        rel = out_video.relative_to(OUTPUT_ROOT).as_posix()
        job["video_path"] = str(out_video)
        if settings.WORKER_MODE and settings.PUBLIC_BASE_URL:
            job["video_url"] = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/media/{rel}"
        else:
            job["video_url"] = f"/media/{rel}"

        platforms = [p.lower().strip() for p in (req.get("platforms") or []) if p]
        if platforms:
            _set_step(job, "publish", "running", f"Publishing to {platforms}…")
            results = publish_to_platforms(
                video_path=out_video,
                title=req.get("title") or req["topic"],
                description=req.get("topic", ""),
                tags=req.get("tags") or [],
                platforms=platforms,
            )
            job["publish_results"] = [
                {
                    "platform": r.platform,
                    "success": r.success,
                    "post_id": r.post_id,
                    "url": r.url,
                    "message": r.message,
                }
                for r in results
            ]
            _set_step(job, "publish", "done")
        else:
            _set_step(job, "publish", "done", "No platforms selected")

        job["status"] = JobStatus.completed
        job["updated_at"] = _now()
        _save_job(job)
    except Exception as e:
        job["status"] = JobStatus.failed
        job["error"] = str(e)
        job["updated_at"] = _now()
        for s in job["steps"]:
            if s["status"] == "running":
                s["status"] = "error"
                s["message"] = str(e)
        _save_job(job)



class WorkerRunRequest(BaseModel):
    job_id: str
    request: Dict[str, Any]
    callback_url: str
    callback_token: str


@app.post("/internal/worker/run")
async def worker_run(body: WorkerRunRequest, background_tasks: BackgroundTasks):
    if not settings.WORKER_MODE:
        raise HTTPException(status_code=404, detail="Worker endpoint disabled")
    if body.callback_token != settings.WORKER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid worker token")
    job = _load_job(body.job_id) or {
        "job_id": body.job_id,
        "status": JobStatus.queued,
        "created_at": _now(),
        "updated_at": _now(),
        "request": body.request,
        "steps": [{"name": n, "status": "pending", "message": ""} for n in PIPELINE_STEPS],
        "video_url": None,
        "video_path": None,
        "publish_results": None,
        "error": None,
    }
    if job.get("status") == JobStatus.running:
        return {"accepted": True, "job_id": body.job_id}
    job["request"] = body.request
    job["_worker_callback_url"] = body.callback_url
    job["_worker_callback_token"] = body.callback_token
    _jobs[body.job_id] = job
    _save_job(job)
    background_tasks.add_task(_run_pipeline, body.job_id)
    return {"accepted": True, "job_id": body.job_id}


@app.post("/internal/worker/callback")
async def worker_callback(
    payload: Dict[str, Any],
    worker_token: str = Header(default="", alias="X-Worker-Token"),
):
    if worker_token != settings.VIDEO_WORKER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid worker token")
    job_id = payload.get("job_id")
    if not job_id:
        raise HTTPException(status_code=400, detail="Missing job_id")
    local = _load_job(job_id)
    if local is None:
        raise HTTPException(status_code=404, detail="Job not found")
    local.pop("_worker_callback_url", None)
    local.pop("_worker_callback_token", None)
    for key in ("status", "updated_at", "steps", "video_url", "video_path", "publish_results", "error"):
        if key in payload:
            local[key] = payload[key]
    _jobs[job_id] = local
    _save_job(local)
    return {"accepted": True, "job_id": job_id}

@app.get("/health")
def health():
    openai_keys = [settings.OPENAI_API_KEY, *settings.OPENAI_API_KEYS]
    openrouter_keys = [settings.OPENROUTER_API_KEY, *settings.OPENROUTER_API_KEYS]
    gemini_keys = [settings.GEMINI_API_KEY, *settings.GEMINI_API_KEYS]
    return {
        "status": "ok",
        "platforms": list_available_publishers(),
        "output_dir": str(OUTPUT_ROOT),
        "generation": {
            "text_provider": "groq",
            "image_provider_order": settings.image_provider_order(),
            "openai": {
                "configured": any(openai_keys),
                "key_count": sum(bool(k) for k in openai_keys),
                "model": settings.OPENAI_IMAGE_MODEL,
            },
            "openrouter": {
                "configured": any(openrouter_keys),
                "key_count": sum(bool(k) for k in openrouter_keys),
                "model": settings.OPENROUTER_IMAGE_MODEL,
            },
            "gemini": {
                "configured": any(gemini_keys),
                "key_count": sum(bool(k) for k in gemini_keys),
                "model": settings.GEMINI_IMAGE_MODEL,
            },
        },
    }


@app.post("/api/v1/generate", response_model=JobResponse)
async def generate(body: GenerateRequest, background_tasks: BackgroundTasks):
    worker_url = settings.VIDEO_WORKER_URL.strip().rstrip("/")
    if not worker_url:
        try:
            settings.validate_generation()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    job_id = uuid.uuid4().hex
    steps = [{"name": n, "status": "pending", "message": ""} for n in PIPELINE_STEPS]
    job = {
        "job_id": job_id,
        "status": JobStatus.queued,
        "created_at": _now(),
        "updated_at": _now(),
        "request": body.model_dump(),
        "steps": steps,
        "video_url": None,
        "video_path": None,
        "publish_results": None,
        "error": None,
    }
    _jobs[job_id] = job
    _save_job(job)

    worker_url = settings.VIDEO_WORKER_URL.strip().rstrip("/")
    if worker_url and not settings.WORKER_MODE:
        if not settings.PUBLIC_BASE_URL:
            job["status"] = JobStatus.failed
            job["error"] = "VIDEO_WORKER_URL is configured but PUBLIC_BASE_URL is missing."
            _save_job(job)
            raise HTTPException(status_code=500, detail=job["error"])
        callback_url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/internal/worker/callback"
        job["_worker_callback_url"] = callback_url
        job["_worker_callback_token"] = settings.VIDEO_WORKER_TOKEN
        _save_job(job)
        try:
            response = await asyncio.to_thread(
                requests.post,
                f"{worker_url}/internal/worker/run",
                json={
                    "job_id": job_id,
                    "request": body.model_dump(),
                    "callback_url": callback_url,
                    "callback_token": settings.VIDEO_WORKER_TOKEN,
                },
                headers={"X-Worker-Token": settings.VIDEO_WORKER_TOKEN},
                timeout=20,
            )
            response.raise_for_status()
        except (requests.RequestException, ValueError) as exc:
            job["status"] = JobStatus.failed
            job["error"] = f"Unable to dispatch video job to worker: {exc}"
            _save_job(job)
            raise HTTPException(status_code=502, detail=job["error"]) from exc
    else:
        background_tasks.add_task(_run_pipeline, job_id)

    return _job_to_response(job)


@app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    job = _load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@app.get("/api/v1/jobs/{job_id}/video")
def download_video(job_id: str):
    job = _load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("video_url", "").startswith("http"):
        return RedirectResponse(job["video_url"])
    path = job.get("video_path")
    if not path or not Path(path).exists():
        raise HTTPException(status_code=404, detail="Video not ready")
    return FileResponse(path, media_type="video/mp4", filename=Path(path).name)


@app.post("/api/v1/publish")
def publish_only(body: PublishRequest):
    video = Path(body.video_path)
    if not video.exists():
        alt = OUTPUT_ROOT / body.video_path
        if alt.exists():
            video = alt
        else:
            raise HTTPException(status_code=404, detail=f"Video not found: {body.video_path}")

    platforms = [p.lower().strip() for p in body.platforms if p] or None
    results = publish_to_platforms(
        video_path=video,
        title=body.title,
        description=body.description,
        tags=body.tags,
        platforms=platforms,
    )
    return {
        "results": [
            {
                "platform": r.platform,
                "success": r.success,
                "post_id": r.post_id,
                "url": r.url,
                "message": r.message,
            }
            for r in results
        ]
    }


if __name__ == "__main__":
    import os
    import uvicorn

    port = int(os.getenv("PORT", os.getenv("HF_PORT", "7860")))
    reload = os.getenv("UVICORN_RELOAD", "0") == "1"
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=reload)
