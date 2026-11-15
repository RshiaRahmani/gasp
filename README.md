# SHARP 3DGS Studio

A local macOS drag-and-drop web UI for [apple-aiml-research/ml-sharp](https://github.com/apple-aiml-research/ml-sharp) to convert single images into 3D Gaussian Splatting (`.ply`) files and inspect them in an interactive 3D viewer.

## Requirements

- macOS (Apple Silicon recommended)
- Python 3.13
- [`uv`](https://docs.astral.sh/uv/)

## Setup & Run

1. **Install dependencies** (creates `.venv` and installs `ml-sharp` + FastAPI):
   ```bash
   ./manage.sh install
   ```

2. **Start the app**:
   ```bash
   ./start.sh
   ```
   This starts the local server at `http://127.0.0.1:8765` and opens it in your browser.

   > **Note:** On the first prediction, `ml-sharp` downloads its model checkpoint (~2.6 GB) to `~/.cache/torch/hub/checkpoints/`.

## Storage & Cleanup

- You can view disk usage and delete generated jobs or the model cache directly from the **Storage & Cache** panel in the UI.
- To remove the Python virtual environment (`.venv`) via CLI:
  ```bash
  ./manage.sh clean
  ```
- To remove both `.venv` and the cached model checkpoint:
  ```bash
  ./manage.sh clean --all
  ```
