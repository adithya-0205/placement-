from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import whisper
import os
import uuid
from datetime import datetime

from database import get_db
from gd_evaluator import evaluate_gd, is_silent_audio, is_silent_transcript

router = APIRouter()

# Load Whisper model
stt_model = whisper.load_model("base")

# Recordings directory
RECORDINGS_DIR = "recordings"
os.makedirs(RECORDINGS_DIR, exist_ok=True)


@router.post("/gd/submit-audio")
async def evaluate_gd_submission(
    topic_id: int = Form(...),
    username: str = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Evaluate a Group Discussion submission.
    
    1. Save audio file
    2. Transcribe with Whisper
    3. Evaluate with Ollama
    4. Store in MySQL
    5. Return results
    """
    
    # Fetch topic text from id if needed, or use a lookup
    topics_list = [
        "Should artificial intelligence replace human decision-making?",
        "Is remote work better than office work?",
        "Should college education be free for everyone?",
        "Is social media doing more harm than good?",
        "Should cryptocurrencies replace traditional currency?",
        "Is climate change the biggest threat to humanity?",
        "Should there be stricter regulations on tech companies?",
        "Is work-life balance achievable in modern careers?",
        "Should voting be made mandatory?",
        "Is online learning as effective as classroom learning?"
    ]
    topic_text = topics_list[topic_id % len(topics_list)]

    # Generate unique filename
    audio_filename = f"{uuid.uuid4()}_{audio.filename}"
    audio_path = os.path.join(RECORDINGS_DIR, audio_filename)
    
    try:
        # Save uploaded audio
        with open(audio_path, "wb") as f:
            f.write(await audio.read())
        
        # Transcribe audio using Whisper
        print(f"🎙️ Transcribing audio for topic: {topic_text}")
        transcription_result = stt_model.transcribe(audio_path)
        transcript = transcription_result.get("text", "").strip()
        
        # Evaluate using Ollama
        print(f"🤖 Evaluating with Ollama...")
        evaluation = evaluate_gd(topic_text, transcript, audio_path)
        
        # Store evaluation in MySQL
        try:
            db.execute(
                text("""
                    INSERT INTO gd_evaluations 
                    (username, topic, transcript, content_score, communication_score, 
                     feedback, audio_path, timestamp)
                    VALUES (:username, :topic, :transcript, :content_score, 
                             :communication_score, :feedback, :audio_path, :timestamp)
                    """),
                    {
                        "username": username.strip(),
                        "topic": topic_text,
                        "transcript": transcript,
                        "content_score": evaluation["content_score"],
                        "communication_score": evaluation["communication_score"],
                        "feedback": evaluation["feedback"],
                        "audio_path": audio_path,
                        "timestamp": datetime.now()
                    }
            )

            # Persist to unified results table for weekly holistic level-up
            avg_gd_score = (evaluation["content_score"] + evaluation["communication_score"]) / 2
            db.execute(
                text("""
                    INSERT INTO results (username, category, score, area, timestamp) 
                    VALUES (:username, :category, :score, :area, NOW())
                """),
                {
                    "username": username.strip(),
                    "category": "GD",
                    "score": int(avg_gd_score),
                    "area": topic_text[:100]
                }
            )
            db.commit()
            print("✅ Evaluation stored in MySQL")
        except Exception as e:
            print(f"⚠️ Warning: Could not store evaluation in database: {e}")
            db.rollback()

        
        return {
            "status": "success",
            "transcript": evaluation["transcript"],
            "content_score": evaluation["content_score"],
            "communication_score": evaluation["communication_score"],
            "feedback": evaluation["feedback"],
            "ideal_answer": evaluation["ideal_answer"]
        }
        
    except Exception as e:
        print(f"❌ Error in GD evaluation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Optional: Clean up audio file after processing
        # Uncomment if you don't want to keep audio files
        # if os.path.exists(audio_path):
        #     os.remove(audio_path)
        pass


@router.get("/history/{username}")
async def get_gd_history(username: str, db: Session = Depends(get_db)):
    """
    Get GD evaluation history for a user.
    """
    try:
        result = db.execute(
            text("""
                SELECT id, topic, content_score, communication_score, 
                       feedback, timestamp
                FROM gd_evaluations
                WHERE username = :username
                ORDER BY timestamp DESC
                LIMIT 10
            """),
            {"username": username.strip()}
        )
        
        rows = result.fetchall()
        
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "topic": row[1],
                "content_score": row[2],
                "communication_score": row[3],
                "feedback": row[4],
                "timestamp": str(row[5])
            })
        
        return {
            "status": "success",
            "history": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gd/topic")
async def get_gd_topic():
    """
    Get a single random GD topic.
    """
    import random
    topics = [
        "Should artificial intelligence replace human decision-making?",
        "Is remote work better than office work?",
        "Should college education be free for everyone?",
        "Is social media doing more harm than good?",
        "Should cryptocurrencies replace traditional currency?",
        "Is climate change the biggest threat to humanity?",
        "Should there be stricter regulations on tech companies?",
        "Is work-life balance achievable in modern careers?",
        "Should voting be made mandatory?",
        "Is online learning as effective as classroom learning?"
    ]
    
    idx = random.randint(0, len(topics) - 1)
    
    return {
        "status": "success",
        "topic": topics[idx],
        "topic_id": idx
    }


@router.get("/topics")
async def get_gd_topics():
    """
    Get list of available GD topics.
    """
    topics = [
        "Should artificial intelligence replace human decision-making?",
        "Is remote work better than office work?",
        "Should college education be free for everyone?",
        "Is social media doing more harm than good?",
        "Should cryptocurrencies replace traditional currency?",
        "Is climate change the biggest threat to humanity?",
        "Should there be stricter regulations on tech companies?",
        "Is work-life balance achievable in modern careers?",
        "Should voting be made mandatory?",
        "Is online learning as effective as classroom learning?"
    ]
    
    return {
        "status": "success",
        "topics": topics
    }