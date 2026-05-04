# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A local timelapse recording desktop application (Windows) with the following capabilities:

- Record timelapse video from a **webcam** or a **Nikon D3300 via USB**
- Save recordings as `.mp4` to `c:\Projetos\timelapseProject\videos`
- Automatically post-process each recording to produce a **social-media version** (re-encoded crop/resize) while keeping the original
- Live preview and playback interface
- USB camera control: expose/adjust Nikon D3300 parameters (shutter speed, aperture, ISO, interval) from the UI via gPhoto2 or digiKam SDK / libgphoto2 on Windows

## Key Design Decisions (from `ideias.md`)

- Output directory is hardcoded: `c:\Projetos\timelapseProject\videos`
- Two output files per session: `original_<timestamp>.mp4` and `social_<timestamp>.mp4`
- The UI must support: start/stop recording, live webcam preview, playback of saved files, and Nikon D3300 remote control over USB
