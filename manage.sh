#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"
VENV_DIR=".venv"
TORCH_CACHE="$HOME/.cache/torch/hub/checkpoints"

usage() {
  echo "Usage: ./manage.sh [install | clean | clean --all]"
  echo ""
  echo "Commands:"
  echo "  install      Create .venv and install ml-sharp + UI dependencies"
  echo "  clean        Delete .venv (all downloaded Python packages)"
  echo "  clean --all  Delete .venv AND cached SHARP model checkpoints (~/.cache/torch/hub/checkpoints)"
}

case "${1:-}" in
  install)
    echo "Creating Python 3.13 virtual environment..."
    uv venv "$VENV_DIR" --python 3.13
    echo "Installing ml-sharp and UI dependencies..."
    VIRTUAL_ENV="$(pwd)/$VENV_DIR" uv pip install -r ml-sharp/requirements.txt fastapi uvicorn python-multipart
    echo "Done! Run ./start.sh to launch the UI."
    ;;
  clean)
    if [ -d "$VENV_DIR" ]; then
      echo "Removing $VENV_DIR..."
      rm -rf "$VENV_DIR"
      echo "Removed $VENV_DIR."
    else
      echo "$VENV_DIR does not exist."
    fi
    if [ "${2:-}" = "--all" ]; then
      if [ -d "$TORCH_CACHE" ]; then
        echo "Removing cached model checkpoints at $TORCH_CACHE..."
        rm -rf "$TORCH_CACHE"
        echo "Removed $TORCH_CACHE."
      else
        echo "No cached model checkpoints found at $TORCH_CACHE."
      fi
    fi
    ;;
  *)
    usage
    exit 1
    ;;
esac
