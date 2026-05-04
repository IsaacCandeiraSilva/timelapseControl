import shutil

OUTPUT_DIR = r"C:\Projetos\timelapseProject\videos"
WEBCAM_INDEX = 0
DEFAULT_CAPTURE_INTERVAL = 1.0  # seconds between timelapse frames
PREVIEW_FPS = 30
TIMELAPSE_PLAYBACK_FPS = 30     # FPS used when encoding the final video

# FFmpeg: use PATH first, fall back to winget install location
FFMPEG_BIN: str = shutil.which("ffmpeg") or (
    r"C:\Users\isaac\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
)
