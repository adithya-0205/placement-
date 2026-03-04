from database import SessionLocal, get_db
from ollama_eval import evaluate_gd
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
import subprocess
import whisper
import os
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel

class GDResponse(BaseModel):
    topic: str
    transcript: str
    content_score: int
    communication_score: int
    camera_score: int
    final_score: int
    feedback: str
    camera_feedback: str
    ideal_answer: str


router = APIRouter()

# ---------------- LOAD WHISPER ONCE ----------------
whisper_model = whisper.load_model("base")


# ---------------- DB Dependency ----------------
# Overriding get_db to ensure it uses the one passed in if needed, 
# but the request provided a specific implementation.

# =================================================
# 1️⃣ FETCH RANDOM GD TOPIC
# =================================================
@router.get("/gd/topic")
def get_gd_topic(db: Session = Depends(get_db)):
    # Debug: Check if the table has ANY data first
    count = db.execute(text("SELECT COUNT(*) FROM gd_topics")).scalar()
    print(f"DEBUG: Total topics in database: {count}")

    result = db.execute(
        text("SELECT id, topic FROM gd_topics ORDER BY RAND() LIMIT 1")
    ).fetchone()

    if not result:
        print("DEBUG: No result returned from query")
        raise HTTPException(status_code=404, detail="No GD topics found")

    print(f"DEBUG: Selected Topic ID: {result[0]}")
    
    return {
        "topic_id": result[0],
        "topic": result[1]
    }


# =================================================
# 2️⃣ SUBMIT AUDIO + VIDEO + FULL AI EVALUATION
# =================================================
@router.post("/submit", response_model=GDResponse)
async def submit_gd(
    topic_id: int = Form(...),
    audio: UploadFile = File(...),
    video: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    os.makedirs("uploads", exist_ok=True)

    # ---------- SAVE AUDIO ----------
    raw_audio_path = f"uploads/{uuid.uuid4()}_{audio.filename}"

    with open(raw_audio_path, "wb") as f:
        f.write(await audio.read())

    # ---------- SAVE VIDEO ----------
    video_path = f"uploads/{uuid.uuid4()}_{video.filename}"

    with open(video_path, "wb") as f:
        f.write(await video.read())

    # ---------- CONVERT AUDIO TO WAV ----------
    if raw_audio_path.lower().endswith(".wav"):
        wav_path = raw_audio_path
    else:
        wav_path = raw_audio_path.rsplit(".", 1)[0] + ".wav"

        process = subprocess.run(
            ["ffmpeg", "-y", "-i", raw_audio_path, wav_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=60
        )


        if process.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Audio conversion failed: {process.stderr}"
            )

    # ---------- TRANSCRIBE ----------
    result = whisper_model.transcribe(wav_path)
    transcript = result["text"].strip()

    # ---------- FETCH TOPIC ----------
    topic_row = db.execute(
        text("SELECT topic FROM gd_topics WHERE id = :id"),
        {"id": topic_id}
    ).fetchone()

    if not topic_row:
        raise HTTPException(status_code=400, detail="Invalid topic ID")

    topic_text = topic_row.topic

    # ---------- INSERT INITIAL ROW ----------
    insert = db.execute(
        text("""
            INSERT INTO gd_results (topic_id, user_answer)
            VALUES (:tid, :ans)
        """),
        {"tid": topic_id, "ans": transcript}
    )
    db.commit()
    gd_id = insert.lastrowid

    # ---------- AI EVALUATION ----------
    evaluation = evaluate_gd(
        topic=topic_text,
        transcript=transcript,
        audio_path=wav_path,
        video_path=video_path
    )

    # ---------- CLEANUP FILES ----------
    for path in [raw_audio_path, wav_path, video_path]:
        if os.path.exists(path):
            os.remove(path)

    # ---------- UPDATE DB ----------
    db.execute(
        text("""
            UPDATE gd_results
            SET content_score = :cs,
                communication_score = :coms,
                camera_score = :cams,
                final_score = :fs,
                feedback = :fb,
                ideal_answer = :ideal
            WHERE id = :id
        """),
        {
            "id": gd_id,
            "cs": evaluation["content_score"],
            "coms": evaluation["communication_score"],
            "cams": evaluation["camera_score"],
            "fs": evaluation["final_score"],
            "fb": evaluation["feedback"],
            "ideal": evaluation["ideal_answer"],
        }
    )
    db.commit()
    
    print("FINAL OUTPUT:", evaluation)

    # ---------- RESPONSE ----------
    return {
        "topic": topic_text,
        "transcript": transcript,
        "content_score": evaluation["content_score"],
        "communication_score": evaluation["communication_score"],
        "camera_score": evaluation["camera_score"],
        "final_score": evaluation["final_score"],
        "feedback": evaluation["feedback"],
        "camera_feedback": evaluation["camera_feedback"],
        "ideal_answer": evaluation["ideal_answer"],
    }