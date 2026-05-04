"""
Tests for NikonThread state machine — NikonClient is mocked; no HTTP calls made.
"""
import threading
from unittest.mock import MagicMock

import numpy as np
import pytest

from capture.nikon import NikonThread


def _make_thread(**kwargs) -> NikonThread:
    client = MagicMock()
    client.ping.return_value = False
    return NikonThread(client=client, **kwargs)


# ------------------------------------------------------------------ initial state

def test_initial_not_recording():
    assert _make_thread()._recording is False


def test_initial_frames_empty():
    assert _make_thread()._captured_frames == []


def test_initial_running_false():
    assert _make_thread()._running is False


# ------------------------------------------------------------------ start_recording

def test_start_recording_sets_flag():
    t = _make_thread()
    t.start_recording(5.0)
    assert t._recording is True


def test_start_recording_stores_interval():
    t = _make_thread()
    t.start_recording(10.0)
    assert t._capture_interval == 10.0


def test_start_recording_clears_previous_frames():
    t = _make_thread()
    with t._frames_lock:
        t._captured_frames.append(np.zeros((10, 10, 3), dtype=np.uint8))
    t.start_recording(5.0)
    assert t._captured_frames == []


def test_start_recording_resets_last_capture_time():
    t = _make_thread()
    t._last_capture_time = 999.0
    t.start_recording(5.0)
    assert t._last_capture_time == 0.0


# ------------------------------------------------------------------ stop_recording

def test_stop_recording_clears_flag():
    t = _make_thread()
    t.start_recording(5.0)
    t.stop_recording()
    assert t._recording is False


def test_stop_recording_returns_frames():
    t = _make_thread()
    t.start_recording(5.0)
    fake = np.zeros((480, 640, 3), dtype=np.uint8)
    with t._frames_lock:
        t._captured_frames.append(fake)
    frames = t.stop_recording()
    assert len(frames) == 1


def test_stop_recording_returns_copy():
    t = _make_thread()
    t.start_recording(5.0)
    with t._frames_lock:
        t._captured_frames.append(np.zeros((10, 10, 3), dtype=np.uint8))
    frames = t.stop_recording()
    t._captured_frames.clear()
    assert len(frames) == 1  # copy is independent


def test_stop_recording_empty_when_no_frames():
    t = _make_thread()
    t.start_recording(5.0)
    assert t.stop_recording() == []


# ------------------------------------------------------------------ restart

def test_second_session_starts_fresh():
    t = _make_thread()
    t.start_recording(5.0)
    with t._frames_lock:
        t._captured_frames.append(np.zeros((10, 10, 3), dtype=np.uint8))
    t.stop_recording()
    t.start_recording(5.0)
    assert t._captured_frames == []


# ------------------------------------------------------------------ _do_capture

def test_do_capture_stores_frame_and_emits_count():
    import cv2
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", frame)

    client = MagicMock()
    client.capture.return_value = "/tmp/test.jpg"

    t = NikonThread(client=client)
    t.start_recording(5.0)

    counts: list[int] = []
    t.timelapse_frame.connect(counts.append)

    # mock cv2.imread to return a frame without touching the filesystem
    import unittest.mock
    with unittest.mock.patch("capture.nikon.cv2.imread", return_value=frame):
        t._do_capture()

    assert len(t._captured_frames) == 1
    assert counts == [1]


def test_do_capture_emits_error_when_capture_returns_none():
    client = MagicMock()
    client.capture.return_value = None

    t = NikonThread(client=client)
    t.start_recording(5.0)

    errors: list[str] = []
    t.camera_error.connect(errors.append)
    t._do_capture()

    assert len(errors) == 1
    assert len(t._captured_frames) == 0


def test_do_capture_emits_error_when_imread_fails():
    client = MagicMock()
    client.capture.return_value = "/tmp/bad.jpg"

    t = NikonThread(client=client)
    t.start_recording(5.0)

    errors: list[str] = []
    t.camera_error.connect(errors.append)

    import unittest.mock
    with unittest.mock.patch("capture.nikon.cv2.imread", return_value=None):
        t._do_capture()

    assert len(errors) == 1
    assert len(t._captured_frames) == 0
