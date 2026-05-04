"""
Tests for capture/webcam.py — state machine only, no real camera required.
"""
import numpy as np
import pytest

from capture.webcam import WebcamThread


# ------------------------------------------------------------------ initial state

def test_initial_state_not_recording():
    t = WebcamThread()
    assert t._recording is False


def test_initial_captured_frames_empty():
    t = WebcamThread()
    assert t._captured_frames == []


def test_initial_running_false():
    t = WebcamThread()
    assert t._running is False


# ------------------------------------------------------------------ start_recording

def test_start_recording_sets_flag():
    t = WebcamThread()
    t.start_recording(1.0)
    assert t._recording is True


def test_start_recording_stores_interval():
    t = WebcamThread()
    t.start_recording(2.5)
    assert t._capture_interval == 2.5


def test_start_recording_clears_previous_frames():
    t = WebcamThread()
    with t._frames_lock:
        t._captured_frames.append(np.zeros((10, 10, 3), dtype=np.uint8))
    t.start_recording(1.0)
    assert t._captured_frames == []


def test_start_recording_resets_last_capture_time():
    t = WebcamThread()
    t._last_capture_time = 999.0
    t.start_recording(1.0)
    assert t._last_capture_time == 0.0


# ------------------------------------------------------------------ stop_recording

def test_stop_recording_clears_flag():
    t = WebcamThread()
    t.start_recording(1.0)
    t.stop_recording()
    assert t._recording is False


def test_stop_recording_returns_accumulated_frames():
    t = WebcamThread()
    t.start_recording(1.0)
    fake = np.zeros((480, 640, 3), dtype=np.uint8)
    with t._frames_lock:
        t._captured_frames.append(fake)
    frames = t.stop_recording()
    assert len(frames) == 1


def test_stop_recording_returns_copy_not_reference():
    """Mutating the internal list after stop_recording must not affect returned list."""
    t = WebcamThread()
    t.start_recording(1.0)
    with t._frames_lock:
        t._captured_frames.append(np.zeros((10, 10, 3), dtype=np.uint8))
    frames = t.stop_recording()
    t._captured_frames.clear()
    assert len(frames) == 1


def test_stop_recording_returns_empty_when_no_frames():
    t = WebcamThread()
    t.start_recording(1.0)
    frames = t.stop_recording()
    assert frames == []


# ------------------------------------------------------------------ restart

def test_restart_clears_frames_from_previous_session():
    t = WebcamThread()
    t.start_recording(1.0)
    with t._frames_lock:
        t._captured_frames.append(np.zeros((10, 10, 3), dtype=np.uint8))
    t.stop_recording()

    t.start_recording(1.0)  # second session
    frames = t.stop_recording()
    assert frames == []


def test_restart_uses_new_interval():
    t = WebcamThread()
    t.start_recording(1.0)
    t.stop_recording()
    t.start_recording(3.0)
    assert t._capture_interval == 3.0
