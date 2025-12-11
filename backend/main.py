import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

# Add project root to path for script imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from backend.routers import generate

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure output directories exist
    output_dirs = ["output", "output/icon", "output/cta", "output/card", "output/boon", "output/gacha"]
    for d in output_dirs:
        Path(PROJECT_ROOT / d).mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(
    title="UNGODLY Asset Generator",
    description="AI-powered UI asset generation for games",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (must be before static files)
app.include_router(generate.router, prefix="/api", tags=["generation"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Serve generated files for download
output_path = PROJECT_ROOT / "output"
if output_path.exists():
    app.mount("/downloads", StaticFiles(directory=str(output_path)), name="downloads")

# Serve static frontend files (must be last - catches all other routes)
static_path = PROJECT_ROOT / "static"
if static_path.exists():
    app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
