import os, tempfile, asyncio
from typing import Optional
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import httpx

app = FastAPI(title="Transcription Gateway", version="1.0.0")

# Env vars
N8N_WEBHOOK = os.getenv("N8N_WEBHOOK", "http://localhost:5678/webhook-test/231e3948-2695-4f37-ab30-0fbd5b75535d")
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/run/transcribe")
async def run_via_n8n(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    translate: bool = Form(False),
):
    """
    Public endpoint for clients/Swagger -> forwards to n8n Webhook.
    The Webhook node must have Binary Data enabled with property name 'file'.
    """
    if not N8N_WEBHOOK:
        raise HTTPException(500, "N8N_WEBHOOK not configured")

    # Build multipart form for n8n
    files = {
        "file": (file.filename or "audio", await file.read(), file.content_type or "application/octet-stream")
    }
    data = {}
    if language is not None:
        data["language"] = language
    data["translate"] = "true" if translate else "false"

    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(N8N_WEBHOOK, files=files, data=data)
    # Bubble up n8n's response
    ctype = r.headers.get("content-type", "")
    if r.status_code >= 400:
        raise HTTPException(r.status_code, r.text)
    return JSONResponse(r.json() if "application/json" in ctype else {"result": r.text})