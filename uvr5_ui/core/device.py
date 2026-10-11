"""Compute device detection. torch is imported lazily because it's slow to load."""

import functools


@functools.lru_cache(maxsize=1)
def get_device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def use_autocast() -> bool:
    return get_device() == "cuda"
