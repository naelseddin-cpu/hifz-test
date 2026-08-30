#!/usr/bin/env python3
"""
Quran Trainer Backend
=====================
Handles all heavy processing:
  - Receives audio clips from mobile clients
  - Runs OpenAI Whisper for Arabic speech-to-text
  - Compares recitation against expected ayah text
  - Returns accuracy score + word-level diff

Install:
  pip install -r requirements.txt

Run:
  python server.py

Requirements:
  - Python 3.8+
  - ffmpeg installed on system (whisper needs it)
  - ~150MB download on first run (whisper base model)
"""

import os
import io
import re
import json
import tempfile
import difflib
from pathlib import Path
from typing import Optional

import whisper
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# ================== CONFIG ==================
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")  # tiny/base/small/medium/large
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# ================== INIT WHISPER ==================
print(f"[INIT] Loading Whisper model: {MODEL_SIZE} ...")
model = whisper.load_model(MODEL_SIZE)
print("[INIT] Whisper ready.")

# ================== FASTAPI ==================
app = FastAPI(title="Quran Trainer API", version="2.0")

# CORS: allow frontend (mobile, file://, localhost, your domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================== ARABIC TEXT UTILS ==================
def normalize_arabic(text: str) -> str:
    """Normalize Arabic for fair comparison (remove diacritics, standardize alef variants)."""
    # Remove tashkeel / diacritics
    text = re.sub(r'[ً-ٰٟـ]', '', text)
    # Standardize alef variants
    text = text.replace('أ', 'ا')  # أ -> ا
    text = text.replace('إ', 'ا')  # إ -> ا
    text = text.replace('آ', 'ا')  # آ -> ا
    text = text.replace('ٱ', 'ا')  # ٱ -> ا
    # Standardize ta marbuta
    text = text.replace('ة', 'ه')  ة -> ه
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def word_diff(expected: str, actual: str):
    """Word-level diff for Arabic. Returns list of word statuses."""
    exp_words = expected.split()
    act_words = actual.split()

    # Use SequenceMatcher for best alignment
    sm = difflib.SequenceMatcher(None, exp_words, act_words)
    result = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for w in exp_words[i1:i2]:
                result.append({"word": w, "status": "correct"})
        elif tag == 'replace':
            # Expected words that were wrong
            for w in exp_words[i1:i2]:
                result.append({"word": w, "status": "wrong"})
            # Extra words spoken (not in expected)
            for w in act_words[j1:j2]:
                result.append({"word": w, "status": "extra"})
        elif tag == 'delete':
            for w in exp_words[i1:i2]:
                result.append({"word": w, "status": "missing"})
        elif tag == 'insert':
            for w in act_words[j1:j2]:
                result.append({"word": w, "status": "extra"})

    # Calculate accuracy
    correct = sum(1 for r in result if r["status"] == "correct")
    total_expected = len(exp_words)
    accuracy = round((correct / total_expected) * 100, 1) if total_expected else 0

    return {"words": result, "accuracy": accuracy, "expected_count": total_expected, "actual_count": len(act_words)}

# ================== ENDPOINTS ==================
@app.get("/")
def root():
    return {"status": "Quran Trainer API is running", "model": MODEL_SIZE}

@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: Optional[str] = Form("ar")
):
    """
    Receive audio blob, run Whisper, return Arabic text.
    Supports: webm, ogg, mp3, wav, m4a
    """
    if not audio.content_type or not audio.content_type.startswith(("audio/", "video/webm")):
        raise HTTPException(400, "File must be audio")

    # Save to temp file (whisper needs a file path)
    suffix = Path(audio.filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = model.transcribe(tmp_path, language=language, fp16=False)
        text = result.get("text", "").strip()
        return {
            "success": True,
            "text": text,
            "language": language,
            "duration": result.get("duration", 0)
        }
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {str(e)}")
    finally:
        os.unlink(tmp_path)

@app.post("/evaluate")
async def evaluate_recitation(
    audio: UploadFile = File(...),
    expected: str = Form(...),           # The exact ayah text expected
    expected_normalized: Optional[str] = Form(None),
    language: Optional[str] = Form("ar")
):
    """
    Full pipeline: transcribe audio + compare against expected ayah.
    Returns: transcription, word-level diff, accuracy %.
    """
    # 1. Transcribe
    if not audio.content_type or not audio.content_type.startswith(("audio/", "video/webm")):
        raise HTTPException(400, "File must be audio")

    suffix = Path(audio.filename).suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await audio.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = model.transcribe(tmp_path, language=language, fp16=False)
        recognized = result.get("text", "").strip()
    except Exception as e:
        raise HTTPException(500, f"Transcription failed: {str(e)}")
    finally:
        os.unlink(tmp_path)

    # 2. Compare
    exp_norm = expected_normalized or normalize_arabic(expected)
    rec_norm = normalize_arabic(recognized)
    diff = word_diff(exp_norm, rec_norm)

    return {
        "success": True,
        "recognized": recognized,
        "recognized_normalized": rec_norm,
        "expected": expected,
        "expected_normalized": exp_norm,
        "accuracy": diff["accuracy"],
        "word_diff": diff["words"],
        "duration": result.get("duration", 0)
    }

@app.get("/surah/{surah_num}")
def get_surah(surah_num: int):
    """Proxy / cache endpoint for Quran text (optional — frontend can call alquran.cloud directly)."""
    import urllib.request
    try:
        url = f"https://api.alquran.cloud/v1/surah/{surah_num}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data["data"]
    except Exception as e:
        raise HTTPException(502, f"Failed to fetch surah: {str(e)}")

# ================== RUN ==================
if __name__ == "__main__":
    print(f"[START] Server running at http://{HOST}:{PORT}")
    print(f"[INFO]  Whisper model: {MODEL_SIZE}")
    print(f"[INFO]  Endpoints: GET /, POST /transcribe, POST /evaluate, GET /surah/{{n}}")
    uvicorn.run(app, host=HOST, port=PORT)
