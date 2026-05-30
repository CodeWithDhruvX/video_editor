"""
FastAPI Application Entry Point
Automation Video Editor & YouTube Uploader
"""

import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers.editor import router as editor_router
from routers.uploader import router as uploader_router

# ─────────────────────────── App Setup ───────────────────────────

def cleanup_old_tokens():
    tokens_dir = Path("tokens")
    if not tokens_dir.exists():
        return
    current_time = time.time()
    five_days_in_seconds = 5 * 24 * 60 * 60
    for file_path in tokens_dir.glob("*.json"):
        try:
            if current_time - file_path.stat().st_mtime > five_days_in_seconds:
                os.remove(file_path)
                print(f"Cleaned up old token file: {file_path}")
        except Exception as e:
            print(f"Failed to cleanup {file_path}: {e}")

app = FastAPI(
    title="Automation Video Editor & Uploader API",
    description="REST API + WebSocket backend for the Video Editor and YouTube Uploader web app.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

@app.on_event("startup")
async def startup_event():
    cleanup_old_tokens()

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # Alternative React dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────── Routers ───────────────────────────

app.include_router(editor_router)
app.include_router(uploader_router)

# ─────────────────────────── Static Files ───────────────────────────

# Serve output files for download preview
outputs_dir = Path("outputs")
outputs_dir.mkdir(exist_ok=True)
app.mount("/static/outputs", StaticFiles(directory=str(outputs_dir)), name="outputs")


# ─────────────────────────── Health Check ───────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "message": "Automation Video Editor & Uploader API is running",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Automation Video Editor & Uploader API",
        "docs": "/docs",
        "health": "/health",
    }


# ─────────────────────────── Entry Point ───────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
