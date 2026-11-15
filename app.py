import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent
JOBS_DIR = BASE_DIR / "jobs"
STATIC_DIR = BASE_DIR / "static"
SHARP_BIN = BASE_DIR / ".venv" / "bin" / "sharp"

JOBS_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(title="SHARP 3DGS Studio")


@app.get("/", response_class=HTMLResponse)
async def index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return index_path.read_text(encoding="utf-8")


@app.post("/api/predict")
async def predict(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    job_id = uuid.uuid4().hex[:8]
    job_dir = JOBS_DIR / job_id
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_inputs = []
    for f in files:
        if not f.filename:
            continue
        safe_name = Path(f.filename).name
        dest = input_dir / safe_name
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        saved_inputs.append(safe_name)

    if not saved_inputs:
        raise HTTPException(status_code=400, detail="No valid files uploaded")

    sharp_cmd = str(SHARP_BIN) if SHARP_BIN.exists() else "sharp"
    cmd = [sharp_cmd, "predict", "-i", str(input_dir), "-o", str(output_dir)]

    env = os.environ.copy()
    env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="SHARP prediction timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run sharp: {e}")

    if proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"SHARP failed (exit {proc.returncode}):\n{proc.stderr}\n{proc.stdout}",
        )

    ply_files = []
    input_images = sorted([p for p in input_dir.iterdir() if p.is_file()])
    for p in sorted(output_dir.glob("*.ply")):
        match = next((img for img in input_images if img.stem == p.stem), input_images[0] if input_images else None)
        ply_files.append(
            {
                "name": p.name,
                "url": f"/api/files/{job_id}/{p.name}",
                "preview_url": f"/api/inputs/{job_id}/{match.name}" if match else None,
                "size_bytes": p.stat().st_size,
            }
        )

    return {
        "job_id": job_id,
        "inputs": saved_inputs,
        "outputs": ply_files,
        "logs": (proc.stdout or "") + "\n" + (proc.stderr or ""),
    }


@app.get("/api/files/{job_id}/{filename}")
async def get_file(job_id: str, filename: str):
    safe_name = Path(filename).name
    file_path = JOBS_DIR / job_id / "output" / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=file_path,
        filename=safe_name,
        media_type="application/octet-stream",
    )


@app.get("/api/inputs/{job_id}/{filename}")
async def get_input_file(job_id: str, filename: str):
    safe_name = Path(filename).name
    file_path = JOBS_DIR / job_id / "input" / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Input file not found")
    return FileResponse(path=file_path)


@app.get("/api/jobs")
async def list_jobs():
    jobs = []
    if not JOBS_DIR.exists():
        return {"jobs": []}
    for job_dir in sorted(JOBS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not job_dir.is_dir():
            continue
        output_dir = job_dir / "output"
        input_dir = job_dir / "input"
        if not output_dir.exists():
            continue
        input_images = sorted([p for p in input_dir.iterdir() if p.is_file()]) if input_dir.exists() else []
        plys = []
        for p in sorted(output_dir.glob("*.ply")):
            match = next((img for img in input_images if img.stem == p.stem), input_images[0] if input_images else None)
            plys.append(
                {
                    "name": p.name,
                    "url": f"/api/files/{job_dir.name}/{p.name}",
                    "preview_url": f"/api/inputs/{job_dir.name}/{match.name}" if match else None,
                    "size_bytes": p.stat().st_size,
                }
            )
        if plys:
            jobs.append({"job_id": job_dir.name, "outputs": plys})
    return {"jobs": jobs[:20]}


@app.post("/api/open-finder/{job_id}")
async def open_finder(job_id: str):
    output_dir = JOBS_DIR / job_id / "output"
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Job output not found")
    subprocess.Popen(["open", str(output_dir)])
    return {"ok": True}


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


@app.get("/api/storage")
async def get_storage():
    torch_cache = Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
    venv_dir = BASE_DIR / ".venv"
    return {
        "jobs_bytes": _dir_size(JOBS_DIR),
        "model_cache_bytes": _dir_size(torch_cache),
        "venv_bytes": _dir_size(venv_dir),
    }


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    safe_id = Path(job_id).name
    job_dir = JOBS_DIR / safe_id
    if not job_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    shutil.rmtree(job_dir)
    return {"ok": True}


@app.post("/api/storage/clear-jobs")
async def clear_jobs():
    if JOBS_DIR.exists():
        for item in JOBS_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    return {"ok": True}


@app.post("/api/storage/clear-cache")
async def clear_cache():
    torch_cache = Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
    if torch_cache.exists():
        shutil.rmtree(torch_cache)
    return {"ok": True}


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
