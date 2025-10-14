# main.py
import os
import tempfile
import json
import re
import warnings
import sqlite3
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import aiofiles

# optional dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# try new OpenAI client
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# Config & client init
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client: Optional[OpenAI] = None
if OPENAI_API_KEY and OpenAI is not None:
    client = OpenAI(api_key=OPENAI_API_KEY)
else:
    warnings.warn("OPENAI_API_KEY not set or OpenAI client not installed. Set env or create .env file.")

ASR_MODEL = "whisper-1"
SUMMARY_MODEL = "gpt-3.5-turbo"

# App and template init
app = FastAPI(title="Meeting Summarizer with DB")
os.makedirs("static", exist_ok=True)
templates = Jinja2Templates(directory="templates")

DB_PATH = "meetings.db"


# --- Simple SQLite helpers ---
def get_db_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            transcript TEXT,
            title TEXT,
            summary TEXT,
            decisions_json TEXT,
            actions_json TEXT,
            notes TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


# --- Helpers ---
async def save_upload_tmp(upload_file: UploadFile) -> str:
    suffix = os.path.splitext(upload_file.filename)[1] or ".wav"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    async with aiofiles.open(path, "wb") as out_file:
        content = await upload_file.read()
        await out_file.write(content)
    return path


def build_summary_prompt(transcript: str, extra_instructions: str = "") -> str:
    prompt = f"""
You are a meeting summarizer assistant.

Task:
1) Produce a concise, structured meeting summary with a short title (1 line).
2) List key decisions / outcomes (bulleted, 1-5 items).
3) Extract action items as a numbered list. For each action include:
   - task (short)
   - assignee (if mentioned; else "TBD")
   - due date (if mentioned; else "TBD")
   - short rationale (1 sentence)
4) Provide key timestamps or speakers if present (optional).
5) Keep the whole output easy to copy/paste.

Transcript:
---
{transcript}
---
{extra_instructions}
Return the result as JSON with keys: title, summary, decisions (list), action_items (list of objects), notes.
"""
    return prompt.strip()


# --- Routes & API ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload", response_class=JSONResponse)
async def upload_audio(file: UploadFile = File(...), prompt_instructions: str = Form("")):
    # check client
    if client is None:
        return JSONResponse(
            {"error": "OPENAI_API_KEY not set or OpenAI client not available on server. Set the env var or .env file."},
            status_code=500,
        )

    tmp_path = await save_upload_tmp(file)
    try:
        # 1) ASR transcribe
        try:
            with open(tmp_path, "rb") as audio_file:
                asr_resp = client.audio.transcriptions.create(model=ASR_MODEL, file=audio_file)
        except Exception as e_asr:
            return JSONResponse({"error": f"ASR/transcription error: {str(e_asr)}"}, status_code=500)

        transcript_text = getattr(asr_resp, "text", "") or ""
        if not transcript_text.strip():
            return JSONResponse({"error": "Empty transcript returned from ASR."}, status_code=500)

        # 2) build prompt & call chat completions
        system_msg = (
            "You are a helpful assistant that converts meeting transcripts into clear meeting notes, "
            "decisions, and action items. Keep it concise and action-oriented."
        )
        user_prompt = build_summary_prompt(transcript_text, extra_instructions=prompt_instructions)

        try:
            chat_resp = client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1000,
                temperature=0.2,
            )
        except Exception as e_chat:
            return JSONResponse({"error": f"LLM summarization error: {str(e_chat)}"}, status_code=500)

        # extract llm text
        llm_text = ""
        try:
            if getattr(chat_resp, "choices", None) and len(chat_resp.choices) > 0:
                choice0 = chat_resp.choices[0]
                llm_text = getattr(getattr(choice0, "message", None), "content", None) or ""
                if not llm_text:
                    llm_text = getattr(getattr(choice0, "delta", None), "content", None) or str(choice0)
            else:
                llm_text = str(chat_resp)
        except Exception:
            llm_text = str(chat_resp)

        # parse JSON inside llm_text if present
        parsed = {"title": None, "summary": None, "decisions": [], "action_items": [], "notes": llm_text}
        m = re.search(r"(\{[\s\S]*\})", llm_text)
        if m:
            json_text = m.group(1)
            try:
                j = json.loads(json_text)
                parsed["title"] = j.get("title")
                parsed["summary"] = j.get("summary")
                parsed["decisions"] = j.get("decisions") or []
                parsed["action_items"] = j.get("action_items") or []
                parsed["notes"] = llm_text
            except Exception:
                parsed["notes"] = llm_text
        else:
            lines = [ln.strip() for ln in llm_text.splitlines() if ln.strip()]
            if lines:
                parsed["title"] = lines[0][:120]
                parsed["summary"] = "\n".join(lines[1:6])

        # Save to DB
        conn = get_db_conn()
        c = conn.cursor()
        created_at = datetime.utcnow().isoformat() + "Z"
        c.execute(
            """
            INSERT INTO meetings (filename, transcript, title, summary, decisions_json, actions_json, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file.filename,
                transcript_text,
                parsed.get("title"),
                parsed.get("summary"),
                json.dumps(parsed.get("decisions") or []),
                json.dumps(parsed.get("action_items") or []),
                parsed.get("notes"),
                created_at,
            ),
        )
        mid = c.lastrowid
        conn.commit()
        conn.close()

        return {
            "id": mid,
            "transcript": transcript_text,
            "title": parsed.get("title"),
            "summary": parsed.get("summary"),
            "decisions": parsed.get("decisions"),
            "action_items": parsed.get("action_items"),
            "notes": parsed.get("notes"),
        }
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


@app.get("/api/meetings")
def list_meetings():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT id, filename, title, created_at FROM meetings ORDER BY id DESC LIMIT 200")
    rows = c.fetchall()
    conn.close()
    items = [dict(r) for r in rows]
    return {"meetings": items}


@app.get("/api/meetings/{mid}")
def get_meeting(mid: int):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM meetings WHERE id = ?", (mid,))
    row = c.fetchone()
    conn.close()
    if not row:
        return JSONResponse({"error": "Meeting not found"}, status_code=404)
    rec = dict(row)
    # parse json fields
    try:
        rec["decisions"] = json.loads(rec.get("decisions_json") or "[]")
    except Exception:
        rec["decisions"] = []
    try:
        rec["action_items"] = json.loads(rec.get("actions_json") or "[]")
    except Exception:
        rec["action_items"] = []
    # remove raw json columns
    rec.pop("decisions_json", None)
    rec.pop("actions_json", None)
    return rec


@app.get("/health")
def health():
    return {"status": "ok"}
