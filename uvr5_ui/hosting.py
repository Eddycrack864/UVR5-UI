"""Where UVR5 UI runs: on the user's own machine, or on a Hugging Face Space shared by every visitor.

Read from environment variables that Hugging Face sets, so the same code runs everywhere.
"""

import os


def on_space() -> bool:
    """A Hugging Face Space: one server for every visitor, so nothing may change its files or settings."""
    return bool(os.environ.get("SPACE_ID"))


def on_zerogpu() -> bool:
    """ZeroGPU hardware: the GPU only exists inside functions wrapped with ``gpu()``."""
    return bool(os.environ.get("SPACES_ZERO_GPU"))


def gpu(fn, duration):
    """Run ``fn`` with a ZeroGPU GPU attached, for up to ``duration`` seconds (or ``duration(*args)``).

    ``fn`` runs in another process: its arguments and result must be picklable. Anywhere else ``fn`` is
    returned unchanged.
    """
    if not on_zerogpu():
        return fn
    import spaces  # only installed on Spaces

    return spaces.GPU(duration=duration)(fn)
