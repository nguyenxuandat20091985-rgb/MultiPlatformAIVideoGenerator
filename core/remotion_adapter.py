"""Optional Remotion renderer bridge."""
from __future__ import annotations
import json
import os
import shutil
import subprocess
from pathlib import Path

def render_from_assets(images_dir: Path, audio_path: Path, output_path: Path) -> Path:
    project = os.getenv("REMOTION_PROJECT_DIR", "").strip()
    if not project:
        raise RuntimeError("REMOTION_PROJECT_DIR is not configured")
    root = Path(project)
    if not (root / "package.json").exists() or shutil.which("npx") is None:
        raise RuntimeError("Remotion project or Node.js/npx is missing")
    manifest = root / "factory-input.json"
    images = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    manifest.write_text(json.dumps({
        "images": [str(p.resolve()) for p in images],
        "audio": str(audio_path.resolve()),
        "output": str(output_path.resolve())
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    composition = os.getenv("REMOTION_COMPOSITION", "FactoryVideo")
    proc = subprocess.run(
        ["npx", "remotion", "render", composition, str(output_path)],
        cwd=str(root), text=True, capture_output=True,
        timeout=int(os.getenv("REMOTION_TIMEOUT_SEC", "1800"))
    )
    if proc.returncode:
        raise RuntimeError(f"Remotion failed: {proc.stdout}\n{proc.stderr}")
    if not output_path.exists() or output_path.stat().st_size < 500:
        raise RuntimeError("Remotion completed without a valid MP4")
    return output_path
