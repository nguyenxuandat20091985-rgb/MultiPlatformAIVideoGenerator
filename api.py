#!/usr/bin/env python3
"""
FastAPI backend for MultiPlatformAIVideoGenerator.

Exposes REST endpoints so the Flutter mobile app (or any client) can:
  - start video generation from a topic
  - poll job progress
  - download / preview the finished video
  - publish to YouTube / TikTok / Facebook
"""
from __future__ import annotations

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
    topic: str = Field(..., min_length=3, description="Video topic / subject")
    title: Optional[str] = Field(None, description="Post title (defaults to topic)")
    style: str = Field("educational", description="Video style")
    target_audience: str = Field("general", description="Target audience")
    cta: str = Field("Follow for more!", description="Call to action")
    tags: List[str] = Field(default_factory=list)
    platforms: List[str] = Field(
        default_factory=list,
        description="Platforms to publish: youtube, tiktok, facebook",
    )
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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _init_steps(skip_captions: bool, platforms: List[str]) -> List[Dict[str, str]]:
    names = ["script", "image_prompts", "images", "audio", "compose"]
    if not skip_captions:
        names.append("captions")
    if platforms:
        names.append("publish")
    return [{"name": n, "status": "pending", "message": ""} for n in names]


def _update_step(job: Dict[str, Any], name: str, status: str, message: str = "") -> None:
    for s in job["steps"]:
        if s["name"] == name:
            s["status"] = status
            s["message"] = message
            break
    done = sum(1 for s in job["steps"] if s["status"] == "done")
    total = len(job["steps"]) or 1
    job["progress_percent"] = int(done / total * 100)
    job["updated_at"] = _now()


def _job_to_response(job: Dict[str, Any]) -> JobResponse:
    return JobResponse(
        job_id=job["job_id"],
        status=JobStatus(job["status"]),
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        request=job["request"],
        steps=[JobStep(**s) for s in job["steps"]],
        progress_percent=job.get("progress_percent", 0),
        video_url=job.get("video_url"),
        video_path=job.get("video_path"),
        publish_results=job.get("publish_results"),
        error=job.get("error"),
    )


def _run_pipeline(job_id: str) -> None:
    job = _jobs[job_id]
    req = job["request"]
    job["status"] = JobStatus.running.value
    job["updated_at"] = _now()

    folder_name = req.get("folder_name") or f"job_{job_id[:8]}"
    topic = req["topic"]
    style = req.get("style") or settings.DEFAULT_VIDEO_STYLE
    audience = req.get("target_audience") or settings.DEFAULT_TARGET_AUDIENCE
    cta = req.get("cta") or settings.DEFAULT_CTA
    skip_captions = bool(req.get("skip_captions"))
    platforms = [p.lower().strip() for p in (req.get("platforms") or []) if p]
    title = req.get("title") or topic
    tags = req.get("tags") or []
    description = req.get("description") or ""

    try:
        settings.validate_generation()

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

        _update_step(job, "script", "running", "Generating script with AI...")
        script_data = generate_script(topic, style, audience, cta)
        save_script(script_data, script_path)
        _update_step(job, "script", "done", "Script ready")

        _update_step(job, "image_prompts", "running", "Creating image prompts...")
        generate_image_prompts(script_path, prompts_path)
        _update_step(job, "image_prompts", "done", "Prompts ready")

        _update_step(job, "images", "running", "Generating images (FLUX)...")
        generate_images(prompts_path, images_dir)
        _update_step(job, "images", "done", f"{len(list(images_dir.glob('*.jpeg')))} images")

        _update_step(job, "audio", "running", "Generating voiceover...")
        audio_path = generate_audio(script_path, audio_dir)
        _update_step(job, "audio", "done", "Audio ready")

        _update_step(job, "compose", "running", "Composing video...")
        compose_video(images_dir, audio_path, video_path)
        _update_step(job, "compose", "done", "Video composed")

        out_video = video_path
        if not skip_captions:
            _update_step(job, "captions", "running", "Adding captions...")
            captions_path = generate_captions(audio_path, captions_dir)
            add_captions_to_video(video_path, captions_path, final_path)
            out_video = final_path
            _update_step(job, "captions", "done", "Captions burned in")

        rel = out_video.relative_to(OUTPUT_ROOT).as_posix()
        job["video_path"] = str(out_video)
        job["video_url"] = f"/media/{rel}"

        if platforms:
            _update_step(job, "publish", "running", f"Publishing to {', '.join(platforms)}...")
            results = publish_to_platforms(
                video_path=out_video,
                title=title,
                description=description,
                tags=tags,
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
            _update_step(job, "publish", "done", "Publish finished")

        job["status"] = JobStatus.completed.value
        job["progress_percent"] = 100
        job["updated_at"] = _now()

    except Exception as e:
        job["status"] = JobStatus.failed.value
        job["error"] = str(e)
        job["updated_at"] = _now()
        for s in job["steps"]:
            if s["status"] == "running":
                s["status"] = "error"
                s["message"] = str(e)
                break


@app.get("/health")
def health():
    return {
        "status": "ok",
        "configured_platforms": list_available_publishers(configured_only=True),
        "all_platforms": list_available_publishers(configured_only=False),
    }


@app.get("/api/v1/platforms")
def platforms():
    return {
        "configured": list_available_publishers(configured_only=True),
        "all": list_available_publishers(configured_only=False),
    }


@app.post("/api/v1/generate", response_model=JobResponse)
def start_generate(body: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = uuid.uuid4().hex
    platforms = [p.lower().strip() for p in body.platforms if p]

    job = {
        "job_id": job_id,
        "status": JobStatus.queued.value,
        "created_at": _now(),
        "updated_at": _now(),
        "request": body.model_dump(),
        "steps": _init_steps(body.skip_captions, platforms),
        "progress_percent": 0,
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


@app.get("/api/v1/jobs")
def list_jobs(limit: int = 20):
    items = sorted(_jobs.values(), key=lambda j: j["created_at"], reverse=True)[:limit]
    return [_job_to_response(j) for j in items]


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
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
