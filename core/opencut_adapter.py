"""Optional OpenCut CLI render adapter."""
from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path

class OpenCutError(RuntimeError): pass

def render(project: str, output: Path, cwd: Path) -> Path:
    if shutil.which("npx") is None:
        raise OpenCutError("Node.js/npx is not installed.")
    if not project:
        raise OpenCutError("OPENCUT_PROJECT is empty.")
    proc = subprocess.run(
        ["npx", "opencut-render", project],
        cwd=str(cwd), text=True, capture_output=True,
        timeout=int(os.getenv("OPENCUT_TIMEOUT_SEC", "1800")),
    )
    if proc.returncode:
        raise OpenCutError(f"OpenCut failed: {proc.stdout}\n{proc.stderr}")
    candidates = [cwd/"out"/f"{project}.mp4", cwd/"out"/project/f"{project}.mp4"]
    source = next((p for p in candidates if p.exists() and p.stat().st_size), None)
    if not source:
        raise OpenCutError("OpenCut completed but no MP4 was found in out/.")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    return output
