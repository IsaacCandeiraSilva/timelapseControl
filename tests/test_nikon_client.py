"""
Tests for NikonClient — all HTTP calls are mocked; no digiCamControl needed.
"""
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from capture.nikon import NikonClient


def _mock_response(status_code=200, json_data=None, content=b""):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.content = content
    return r


# ------------------------------------------------------------------ ping

def test_ping_returns_true_on_200():
    with patch("requests.get", return_value=_mock_response(200)):
        assert NikonClient().ping() is True


def test_ping_returns_false_on_connection_error():
    with patch("requests.get", side_effect=ConnectionError):
        assert NikonClient().ping() is False


def test_ping_returns_false_on_non_200():
    with patch("requests.get", return_value=_mock_response(503)):
        assert NikonClient().ping() is False


# ------------------------------------------------------------------ camera_name

def test_camera_name_returns_name_from_session():
    payload = {"Data": [{"Name": "Nikon D3300"}]}
    with patch("requests.get", return_value=_mock_response(json_data=payload)):
        assert NikonClient().camera_name() == "Nikon D3300"


def test_camera_name_returns_empty_on_error():
    with patch("requests.get", side_effect=Exception):
        assert NikonClient().camera_name() == ""


def test_camera_name_returns_empty_when_no_sessions():
    payload = {"Data": []}
    with patch("requests.get", return_value=_mock_response(json_data=payload)):
        assert NikonClient().camera_name() == ""


# ------------------------------------------------------------------ get_property

def test_get_property_returns_value_and_allowed():
    payload = {
        "Status": "ok",
        "Data": "400",
        "AllowedValues": ["100", "200", "400", "800"],
    }
    with patch("requests.get", return_value=_mock_response(json_data=payload)):
        result = NikonClient().get_property("iso")
    assert result["value"] == "400"
    assert result["allowed"] == ["100", "200", "400", "800"]


def test_get_property_uses_mapped_api_name():
    """'iso' must be sent as 'isonumber' to digiCamControl."""
    with patch("requests.get", return_value=_mock_response(json_data={"Status": "ok", "Data": "100"})) as mock_get:
        NikonClient().get_property("iso")
    url = mock_get.call_args[0][0]
    assert "isonumber" in url


def test_get_property_returns_empty_dict_on_error():
    with patch("requests.get", side_effect=Exception):
        assert NikonClient().get_property("iso") == {}


def test_get_property_returns_empty_dict_on_non_ok_status():
    with patch("requests.get", return_value=_mock_response(json_data={"Status": "error"})):
        assert NikonClient().get_property("iso") == {}


# ------------------------------------------------------------------ set_property

def test_set_property_returns_true_on_ok():
    with patch("requests.get", return_value=_mock_response(json_data={"Status": "ok"})):
        assert NikonClient().set_property("iso", "800") is True


def test_set_property_returns_false_on_error_status():
    with patch("requests.get", return_value=_mock_response(json_data={"Status": "error"})):
        assert NikonClient().set_property("iso", "800") is False


def test_set_property_returns_false_on_exception():
    with patch("requests.get", side_effect=Exception):
        assert NikonClient().set_property("iso", "800") is False


def test_set_property_uses_mapped_api_name():
    """'shutter' must be sent as 'shutterspeed'."""
    with patch("requests.get", return_value=_mock_response(json_data={"Status": "ok"})) as mock_get:
        NikonClient().set_property("shutter", "1/60")
    url = mock_get.call_args[0][0]
    assert "shutterspeed" in url


# ------------------------------------------------------------------ capture

def test_capture_returns_file_path_on_success():
    payload = {"Status": "ok", "Data": r"C:\Users\user\Pictures\DSC_0001.jpg"}
    with patch("requests.get", return_value=_mock_response(json_data=payload)):
        path = NikonClient().capture()
    assert path == r"C:\Users\user\Pictures\DSC_0001.jpg"


def test_capture_returns_none_on_error_status():
    with patch("requests.get", return_value=_mock_response(json_data={"Status": "error"})):
        assert NikonClient().capture() is None


def test_capture_returns_none_on_exception():
    with patch("requests.get", side_effect=Exception):
        assert NikonClient().capture() is None


# ------------------------------------------------------------------ get_liveview_frame

def test_get_liveview_frame_returns_none_on_empty_content():
    with patch("requests.get", return_value=_mock_response(200, content=b"")):
        assert NikonClient().get_liveview_frame() is None


def test_get_liveview_frame_returns_none_on_exception():
    with patch("requests.get", side_effect=Exception):
        assert NikonClient().get_liveview_frame() is None


def test_get_liveview_frame_returns_none_on_non_200():
    with patch("requests.get", return_value=_mock_response(500, content=b"data")):
        assert NikonClient().get_liveview_frame() is None


def test_get_liveview_frame_decodes_valid_jpeg():
    import cv2
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", frame)
    with patch("requests.get", return_value=_mock_response(200, content=buf.tobytes())):
        result = NikonClient().get_liveview_frame()
    assert result is not None
    assert result.shape == (240, 320, 3)
