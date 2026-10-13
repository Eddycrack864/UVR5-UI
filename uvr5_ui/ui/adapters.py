"""Glue between Gradio event handlers and the core services."""

import functools
import inspect
import logging

import gradio as gr

from uvr5_ui.core.errors import UVRError
from uvr5_ui.i18n import i18n

logger = logging.getLogger(__name__)

# Concurrency group shared by every GPU-heavy event so two separations never overlap.
GPU_CONCURRENCY_ID = "separation"


def progress_callback(progress: gr.Progress):
    """Adapt ``gr.Progress`` to the core's ``(fraction, description)`` callback."""
    def report(fraction: float, desc: str) -> None:
        progress(fraction, desc=desc)
    return report


def user_errors(func):
    """Show failures as Gradio error toasts instead of raw tracebacks.

    Works for plain functions and generator handlers.
    """
    def to_gr_error(e: Exception) -> gr.Error:
        if isinstance(e, gr.Error):
            return e
        if isinstance(e, UVRError):
            logger.warning("%s", e, exc_info=e.__cause__ is not None)
            return gr.Error(i18n(str(e)))  # some messages are i18n keys; the rest pass through
        logger.exception("Unexpected error in %s", func.__name__)
        return gr.Error(f"{i18n('An unexpected error occurred, check the console for details')}: {e}")

    if inspect.isgeneratorfunction(func):
        @functools.wraps(func)
        def gen_wrapper(*args, **kwargs):
            try:
                yield from func(*args, **kwargs)
            except Exception as e:
                raise to_gr_error(e) from e
        return gen_wrapper

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            raise to_gr_error(e) from e
    return wrapper


def validations(*checks) -> dict:
    """Validator result from ``(component, is_valid, message)`` checks.

    Validators run before the event is queued, so a missing input is flagged on its
    component right away instead of after waiting for the GPU.
    """
    return {component: gr.validate(bool(is_valid), i18n(message)) for component, is_valid, message in checks}


def filled(value) -> bool:
    return value is not None and not (isinstance(value, str) and not value.strip())


def require(value, message: str):
    """Raise a translated Gradio error when a required input is missing."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise gr.Error(i18n(message))
    return value
