# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**timelapseControl** — aplicativo desktop Windows (Python + PyQt6) para gravação de timelapse com webcam ou câmera Nikon D3300 via USB.

Repositório GitHub: `IsaacCandeiraSilva/timelapseControl`

### Funcionalidades implementadas
- Captura timelapse via **webcam** (OpenCV) ou **Nikon D3300** (digiCamControl HTTP API)
- Preview ao vivo durante gravação
- Encoding automático ao parar: gera `original_<timestamp>.mp4` + `social_<timestamp>.mp4` (9:16, 1080×1920)
- Controle de parâmetros da Nikon (ISO, obturador, abertura) direto na UI
- Troca de fonte (Webcam ↔ Nikon) sem reiniciar o app

### Fase pendente
- **Fase 4** — Galeria de gravações + playback interno (issue #4 no GitHub)

---

## Como executar

```bash
py main.py
```

### Dependências
```bash
py -m pip install -r requirements.txt
```
Pacotes: `opencv-python`, `PyQt6`, `numpy`, `requests`, `pytest`

### FFmpeg
Instalado via winget (`Gyan.FFmpeg`). Caminho configurado em `config.py::FFMPEG_BIN` com fallback automático via `shutil.which`.

### digiCamControl (Nikon D3300)
Obrigatório apenas para usar a fonte Nikon. Configuração:
1. Instalar: https://digicamcontrol.com/
2. File → Settings → aba **Webserver** → habilitar na porta **5513**
3. Verificar: `http://localhost:5513/session/list` deve retornar JSON

### Testes
```bash
py -m pytest tests/ -v
```
49 testes passando (sem câmera nem digiCamControl necessários).

---

## Arquitetura

```
timelapseProject/
├── main.py                    # entry point — cria QApplication e MainWindow
├── config.py                  # constantes: OUTPUT_DIR, WEBCAM_INDEX, FFMPEG_BIN, FPS
├── capture/
│   ├── webcam.py              # WebcamThread — OpenCV, preview 30fps, coleta frames timelapse
│   └── nikon.py               # NikonClient (HTTP) + NikonThread — live view 5fps, disparos via HTTP
├── processing/
│   └── encoder.py             # EncoderThread — pipe raw frames → FFmpeg → 2 MP4
├── ui/
│   ├── main_window.py         # MainWindow — janela principal, seletor de fonte, orquestra threads
│   ├── live_view.py           # LiveViewWidget — exibe frames BGR como QPixmap escalado
│   └── controls.py            # NikonControlsWidget — painel ISO/obturador/abertura
├── tests/
│   ├── conftest.py            # QApplication singleton para testes
│   ├── test_webcam.py         # 13 testes — estado da WebcamThread
│   ├── test_encoder.py        # 11 testes — encoding real com FFmpeg (frames sintéticos)
│   ├── test_nikon_client.py   # 21 testes — NikonClient com requests mockado
│   └── test_nikon_thread.py   # 16 testes — estado e _do_capture da NikonThread
└── videos/                    # saída: original_*.mp4 + social_*.mp4
```

### Fluxo de gravação

```
[Start]
  │
  ├── WebcamThread.start_recording(interval)
  │     └── a cada `interval` segundos: frame.copy() → _captured_frames
  │
  └── NikonThread.start_recording(interval)
        └── a cada `interval` segundos: HTTP GET /camera/capturenoaf
              └── cv2.imread(path) → _captured_frames

[Stop]
  │
  └── stop_recording() → list[np.ndarray]
        └── EncoderThread(frames)
              ├── _pipe() → FFmpeg stdin pipe → original_<ts>.mp4
              └── _pipe(vf=crop+scale) → FFmpeg stdin pipe → social_<ts>.mp4
```

### Decisões de design importantes

- **Deadlock de pipe FFmpeg**: `stderr=PIPE` sem leitura paralela trava o `proc.wait()` quando o buffer do OS (~64 KB) enche durante filtros complexos (`crop+scale`). Fix: thread separada drena stderr enquanto stdin é escrito (`processing/encoder.py:_pipe`).
- **Interface uniforme das threads**: `WebcamThread` e `NikonThread` têm a mesma API pública (`start_recording`, `stop_recording`, `stop`, sinais `frame_ready`/`timelapse_frame`/`camera_error`). `MainWindow` troca entre elas sem lógica condicional.
- **Dimensões pares para libx264**: `_even()` arredonda largura/altura para baixo antes de passar ao FFmpeg.
- **Conexão Nikon**: verificada a cada 2 s em background; UI atualiza status automaticamente sem bloquear.
- **Troca de fonte**: bloqueada durante gravação ativa para evitar troca de thread no meio do timelapse.

---

## Comandos git úteis

```bash
git log --oneline        # histórico resumido
py -m pytest tests/ -v  # rodar todos os testes
```
