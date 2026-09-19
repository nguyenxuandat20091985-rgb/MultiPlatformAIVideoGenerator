"""Core video generation pipeline.

Heavy optional media/ML modules are imported lazily so the Render web process
does not load Whisper/PyTorch/MoviePy just to compose a video.
"""
from .script_generator import generate_script, save_script
from .image_prompt_generator import generate_image_prompts
from .image_generator import generate_images
from .audio_generator import generate_audio
from .video_composer import compose_video


def generate_captions(*args, **kwargs):
    from .caption_generator import generate_captions as _generate_captions
    return _generate_captions(*args, **kwargs)


def add_captions_to_video(*args, **kwargs):
    from .caption_overlay import add_captions_to_video as _add_captions_to_video
    return _add_captions_to_video(*args, **kwargs)


__all__ = [
    "generate_script",
    "save_script",
    "generate_image_prompts",
    "generate_images",
    "generate_audio",
    "generate_captions",
    "compose_video",
    "add_captions_to_video",
]
