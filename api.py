#!/usr/bin/env python3
"""
FastAPI backend for MultiPlatformAIVideoGenerator.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from config.settings import settings
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


def _set_step(job: Dict[str, Any], name: str, status: str, message: str = "") -> None:
    for s in job["steps"]:
        if s["name"] == name:
            s["status"] = status
            s["message"] = message
            break
    job["updated_at"] = _now()


def _run_pipeline(job_id: str) -> None:
    job = _jobs[job_id]
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

        _set_step(job, "compose", "running", "Composing video…")
        compose_video(images_dir, audio_path, video_path)
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

        rel = out_video.relative_to(OUTPUT_ROOT).as_posix()
        job["video_path"] = str(out_video)
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
    except Exception as e:
        job["status"] = JobStatus.failed
        job["error"] = str(e)
        job["updated_at"] = _now()
        for s in job["steps"]:
            if s["status"] == "running":
                s["status"] = "error"
                s["message"] = str(e)


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
    background_tasks.add_task(_run_pipeline, job_id)
    return _job_to_response(job)


@app.get("/api/v1/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_to_response(job)


@app.get("/api/v1/jobs/{job_id}/video")
def download_video(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
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
