"""
Tests for processing/encoder.py.
These tests call real FFmpeg with synthetic frames.
Each test uses a tmp_path so no files land in videos/.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

import config
from processing.encoder import EncoderThread

_TIMEOUT_MS = 60_000  # 60 s per test


def _solid_frames(count: int, width: int = 320, height: int = 240) -> list[np.ndarray]:
    """Small solid-colour BGR frames — fast to encode."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (0, 120, 200)  # orange-ish
    return [frame.copy() for _ in range(count)]


def _run(thread: EncoderThread) -> tuple[list[str], list[str]]:
    """Start thread, collect finished/error results, return (results, errors)."""
    results: list[str] = []
    errors: list[str] = []
    thread.finished.connect(
        lambda orig, soc: results.extend([orig, soc]),
        Qt.ConnectionType.DirectConnection,
    )
    thread.error.connect(errors.append, Qt.ConnectionType.DirectConnection)
    thread.start()
    thread.wait(_TIMEOUT_MS)
    return results, errors


# ------------------------------------------------------------------ happy path

def test_both_files_created(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    results, errors = _run(EncoderThread(_solid_frames(10), fps=5))

    assert not errors, errors
    assert len(results) == 2
    assert Path(results[0]).exists(), "original não criado"
    assert Path(results[1]).exists(), "social não criado"


def test_original_preserves_resolution(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    results, errors = _run(EncoderThread(_solid_frames(5, width=320, height=240), fps=5))

    assert not errors, errors
    cap = cv2.VideoCapture(results[0])
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    assert (w, h) == (320, 240)


def test_social_is_portrait_1080x1920(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    results, errors = _run(EncoderThread(_solid_frames(5, width=320, height=240), fps=5))

    assert not errors, errors
    cap = cv2.VideoCapture(results[1])
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    assert (w, h) == (1080, 1920)


def test_original_filename_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    results, errors = _run(EncoderThread(_solid_frames(5), fps=5))

    assert not errors, errors
    assert Path(results[0]).name.startswith("original_")
    assert Path(results[1]).name.startswith("social_")


def test_progress_starts_at_zero_and_ends_at_100(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    values: list[int] = []
    thread = EncoderThread(_solid_frames(10), fps=5)
    thread.progress.connect(values.append, Qt.ConnectionType.DirectConnection)
    thread.start()
    thread.wait(_TIMEOUT_MS)

    assert values, "nenhum progresso emitido"
    assert values[0] >= 0
    assert values[-1] == 100


def test_progress_never_exceeds_100(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    values: list[int] = []
    thread = EncoderThread(_solid_frames(10), fps=5)
    thread.progress.connect(values.append, Qt.ConnectionType.DirectConnection)
    thread.start()
    thread.wait(_TIMEOUT_MS)

    assert all(0 <= v <= 100 for v in values)


# ------------------------------------------------------------------ odd dimensions

def test_odd_width_height_handled(tmp_path, monkeypatch):
    """libx264 requires even dimensions — encoder must round down without crashing."""
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    results, errors = _run(EncoderThread(_solid_frames(5, width=321, height=241), fps=5))

    assert not errors, errors
    assert Path(results[0]).exists()
    assert Path(results[1]).exists()


# ------------------------------------------------------------------ edge cases

def test_empty_frame_list_emits_error(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    results, errors = _run(EncoderThread([], fps=5))

    assert not results
    assert len(errors) == 1
    assert "frame" in errors[0].lower()


def test_single_frame_encodes(tmp_path, monkeypatch):
    """One frame should still produce valid MP4 files."""
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    results, errors = _run(EncoderThread(_solid_frames(1), fps=5))

    assert not errors, errors
    assert Path(results[0]).exists()
    assert Path(results[1]).exists()


def test_output_files_are_not_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DIR", str(tmp_path))
    results, errors = _run(EncoderThread(_solid_frames(5), fps=5))

    assert not errors, errors
    assert Path(results[0]).stat().st_size > 0
    assert Path(results[1]).stat().st_size > 0


def test_output_dir_created_if_missing(tmp_path, monkeypatch):
    nested = str(tmp_path / "sub" / "videos")
    monkeypatch.setattr(config, "OUTPUT_DIR", nested)
    results, errors = _run(EncoderThread(_solid_frames(5), fps=5))

    assert not errors, errors
    assert Path(nested).exists()
