"""
FIXED ADAPTIVE QUIZ SYSTEM
- 10 questions per day
- Progressive difficulty (easy → medium → hard)
- Correct answer validation
- Daily question tracking
"""

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date
import random

from database import get_db

class QuizRequest(BaseModel):
    username: str
    category: str  # "aptitude" or "technical"

class AnswerSubmission(BaseModel):
    username: str
    category: str
    question_id: int
    user_answer: str  # "A", "B", "C", or "D"
    
class QuizCompleteSubmission(BaseModel):
    username: str
    category: str
    score: int
    total_questions: int


def get_user_level(db: Session, username: str, category: str):
    """Get user's current difficulty level"""
    result = db.execute(
        text("SELECT aptitude_level, technical_level FROM users WHERE username = :username"),
        {"username": username}
    )
    user = result.fetchone()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    level = user[0] if category.lower() == "aptitude" else user[1]
    
    # Map level to difficulty
    if level == 1:
        return "easy"
    elif level == 2:
        return "medium"
    else:
        return "hard"


def get_todays_questions(db: Session, username: str, category: str):
    """
    Get 10 questions for today
    - Reuses same questions for the same day
    - Resets daily
    """
    today = date.today()
    
    # Check if user already has questions for today
    result = db.execute(
        text("""
            SELECT question_ids FROM daily_quiz 
            WHERE username = :username 
            AND category = :category 
            AND quiz_date = :today
        """),
        {"username": username, "category": category.lower(), "today": today}
    )
    
    existing = result.fetchone()
    
    if existing and existing[0]:
        # Return existing question IDs
        question_ids = [int(x) for x in existing[0].split(",")]
        return question_ids
    
    # Generate new questions for today
    difficulty = get_user_level(db, username, category)
    
    result = db.execute(
        text("""
            SELECT id FROM questions 
            WHERE category = :category 
            AND difficulty = :difficulty
            ORDER BY RAND()
            LIMIT 10
        """),
        {"category": category.lower(), "difficulty": difficulty}
    )
    
    rows = result.fetchall()
    question_ids = [row[0] for row in rows]
    
    if len(question_ids) < 10:
        raise HTTPException(
            status_code=404, 
            detail=f"Not enough {difficulty} questions available. Only {len(question_ids)} found."
        )
    
    # Save for today
    db.execute(
        text("""
            INSERT INTO daily_quiz (username, category, quiz_date, question_ids)
            VALUES (:username, :category, :today, :ids)
            ON DUPLICATE KEY UPDATE question_ids = :ids
        """),
        {
            "username": username, 
            "category": category.lower(), 
            "today": today,
            "ids": ",".join(map(str, question_ids))
        }
    )
    db.commit()
    
    return question_ids


def get_questions_by_ids(db: Session, question_ids: list):
    """Fetch full question details"""
    placeholders = ",".join([str(id) for id in question_ids])
    
    result = db.execute(
        text(f"""
            SELECT id, question, option_a, option_b, option_c, option_d, 
                   correct_answer, area, explanation, difficulty
            FROM questions 
            WHERE id IN ({placeholders})
        """)
    )
    
    rows = result.fetchall()
    
    # Map to dict for easy lookup
    questions_dict = {}
    for row in rows:
        questions_dict[row[0]] = {
            "id": row[0],
            "question": row[1],
            "options": {
                "A": row[2],
                "B": row[3],
                "C": row[4],
                "D": row[5]
            },
            "correct_answer": row[6],  # This is the LETTER (A/B/C/D)
            "area": row[7] or "General",
            "explanation": row[8] or "No explanation provided.",
            "difficulty": row[9]
        }
    
    # Return in original order
    return [questions_dict[id] for id in question_ids if id in questions_dict]


def validate_answer(db: Session, question_id: int, user_answer: str):
    """
    FIXED: Properly validate user answer
    Returns: (is_correct: bool, correct_answer: str, explanation: str)
    """
    result = db.execute(
        text("SELECT correct_answer, explanation FROM questions WHERE id = :id"),
        {"id": question_id}
    )
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    
    correct_answer = row[0].strip().upper()  # Should be "A", "B", "C", or "D"
    explanation = row[1] or "No explanation provided."
    
    # Normalize user answer
    user_answer = user_answer.strip().upper()
    
    # Compare
    is_correct = (user_answer == correct_answer)
    
    return is_correct, correct_answer, explanation


# ============================================
# API ENDPOINTS
# ============================================

from fastapi import APIRouter

router = APIRouter()


@router.post("/get_daily_quiz")
async def get_daily_quiz(request: QuizRequest, db: Session = Depends(get_db)):
    """
    Get today's 10 questions
    - Same questions for the entire day
    - Resets at midnight
    """
    try:
        question_ids = get_todays_questions(db, request.username, request.category)
        questions = get_questions_by_ids(db, question_ids)
        
        # Don't send correct answers to frontend!
        for q in questions:
            q.pop("correct_answer", None)
            q.pop("explanation", None)
        
        return {
            "status": "success",
            "date": str(date.today()),
            "difficulty": get_user_level(db, request.username, request.category),
            "questions": questions,
            "total": len(questions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check_answer")
async def check_answer(submission: AnswerSubmission, db: Session = Depends(get_db)):
    """
    Check a single answer
    Returns immediate feedback
    """
    try:
        is_correct, correct_answer, explanation = validate_answer(
            db, 
            submission.question_id, 
            submission.user_answer
        )
        
        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": explanation,
            "user_answer": submission.user_answer
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit_quiz")
async def submit_quiz(submission: QuizCompleteSubmission, db: Session = Depends(get_db)):
    """
    Submit completed quiz
    - Updates user level if score is high
    - Saves to results table
    """
    try:
        # Calculate percentage
        percentage = (submission.score / submission.total_questions) * 100
        
        # Save result
        db.execute(
            text("""
                INSERT INTO results (username, category, score, area, timestamp) 
                VALUES (:username, :category, :score, 'Daily Quiz', NOW())
            """),
            {
                "username": submission.username,
                "category": submission.category.upper(),
                "score": submission.score
            }
        )
        
        # Level up logic
        level_up = False
        threshold = 70  # 70% to level up
        
        if percentage >= threshold:
            col = "aptitude_level" if submission.category.lower() == "aptitude" else "technical_level"
            
            # Get current level
            result = db.execute(
                text(f"SELECT {col} FROM users WHERE username = :username"),
                {"username": submission.username}
            )
            current_level = result.fetchone()[0]
            
            # Only level up to max 3 (easy, medium, hard)
            if current_level < 3:
                db.execute(
                    text(f"UPDATE users SET {col} = {col} + 1 WHERE username = :username"),
                    {"username": submission.username}
                )
                level_up = True
        
        db.commit()
        
        return {
            "status": "success",
            "score": submission.score,
            "total": submission.total_questions,
            "percentage": round(percentage, 1),
            "level_up": level_up,
            "message": "Great job! Level up!" if level_up else "Keep practicing!"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quiz_status/{username}/{category}")
async def get_quiz_status(username: str, category: str, db: Session = Depends(get_db)):
    """
    Check if user has already taken today's quiz
    """
    try:
        today = date.today()
        
        result = db.execute(
            text("""
                SELECT question_ids FROM daily_quiz 
                WHERE username = :username 
                AND category = :category 
                AND quiz_date = :today
            """),
            {"username": username, "category": category.lower(), "today": today}
        )
        
        existing = result.fetchone()
        has_quiz_today = existing is not None
        
        # Get current level
        difficulty = get_user_level(db, username, category)
        
        return {
            "has_quiz_today": has_quiz_today,
            "current_level": difficulty,
            "date": str(today)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))