"""
Lightweight progress wrapper to optionally use tqdm.
Falls back gracefully when tqdm is not installed.
"""

from typing import Iterable


def progress_wrap(iterable: Iterable, desc: str = None, unit: str = None):
    try:
        from tqdm import tqdm  # type: ignore
        return tqdm(iterable, desc=desc, unit=unit)
    except Exception:
        # Fallback: no progress bar, just return the iterable
        return iterable