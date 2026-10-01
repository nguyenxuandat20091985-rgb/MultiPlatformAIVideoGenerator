"""Optional ComfyUI HTTP adapter for local AI video/image workflows."""
from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Any
import requests

def submit_workflow(workflow: dict[str, Any]) -> str:
    base = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    response = requests.post(f"{base}/prompt", json={
        "prompt": workflow,
        "client_id": os.getenv("COMFYUI_CLIENT_ID", "video-factory")
    }, timeout=30)
    response.raise_for_status()
    prompt_id = response.json().get("prompt_id")
    if not prompt_id:
        raise RuntimeError("ComfyUI did not return prompt_id")
    return prompt_id

def wait_for_prompt(prompt_id: str) -> dict[str, Any]:
    base = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    deadline = time.time() + int(os.getenv("COMFYUI_TIMEOUT_SEC", "1800"))
    while time.time() < deadline:
        response = requests.get(f"{base}/history/{prompt_id}", timeout=30)
        response.raise_for_status()
        history = response.json()
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(float(os.getenv("COMFYUI_POLL_SEC", "2")))
    raise TimeoutError(f"ComfyUI prompt timed out: {prompt_id}")

def download_output(filename: str, subfolder: str, folder_type: str, destination: Path) -> Path:
    base = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
    response = requests.get(f"{base}/view", params={
        "filename": filename, "subfolder": subfolder, "type": folder_type
    }, timeout=120)
    response.raise_for_status()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination
