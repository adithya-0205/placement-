from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
import whisper 
import ollama  
import json    
import os
import random
import traceback
import sys
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import date, datetime, timedelta, time
import pymysql
from concurrent.futures import ThreadPoolExecutor
import re
from typing import List, Dict, Optional

from database import get_db, init_db, test_connection, SessionLocal, mysql_engine as engine

# --- MODELS ---
class UserAuth(BaseModel):
    username: str
    password: str
    branch: Optional[str] = None
    role: Optional[str] = 'student'

class QuizRequest(BaseModel):
    username: str
    category: str
    target_branch: Optional[str] = None # Added for practice mode

class AnswerSubmission(BaseModel):
    username: str
    category: str
    question_id: int
    user_answer: str

class QuizCompleteSubmission(BaseModel):
    username: str
    category: str
    score: int
    total_questions: int
    target_branch: Optional[str] = None # Added for practice mode
    weak_area: Optional[str] = None # Added for analytics

class QuizResult(BaseModel):
    username: str
    category: str
    score: int
    area: str

class UpdateBranchRequest(BaseModel):
    username: str
    branch: str

# Load Whisper model once at startup
stt_model = whisper.load_model("base")

def process_weekly_level_up(username: str, db: Session):
    """
    Holistic Weekly Level-Up Logic
    - Triggered on Login or Dashboard view
    - Checks if it's Sunday
    - Aggregates scores: Aptitude, Technical, GD, Interview
    - Level up if holistic average >= 7 (70%)
    """
    try:
        today = date.today()
        # Only trigger on Sunday (weekday 6)
        if today.weekday() != 6:
            return False

        # Get user
        user_result = db.execute(
            text("SELECT aptitude_level, technical_level, last_level_update FROM users WHERE username = :u"),
            {"u": username}
        )
        user = user_result.fetchone()
        if not user: return False
        
        apt_lvl, tech_lvl, last_update = user
        
        # Prevent multiple updates in the same week
        if last_update and last_update.date() >= today - timedelta(days=6):
            return False

        # 1. Aggregate Scores from last 7 days from results table
        scores_result = db.execute(
            text("""
                SELECT category, AVG(score) as avg_score, COUNT(*) as count 
                FROM results 
                WHERE username = :u AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY category
            """),
            {"u": username}
        )
        
        results = scores_result.fetchall()
        if not results: return False
        
        cat_scores = {row[0].upper(): row[1] for row in results}

        # 2. Calculate Holistic Metrics
        # Aptitude: 
        apt_avg = cat_scores.get('APTITUDE', 0)
        
        # Technical aggregate: (Tech Quizzes + GD + Interview)
        tech_quizzes = cat_scores.get('TECHNICAL', 0)
        gd_avg = cat_scores.get('GD', 0)
        interview_avg = cat_scores.get('INTERVIEW', 0)
        
        total_activities = sum(row[2] for row in results)

        # Holistic Tech Avg (Average of non-zero modules)
        tech_modules = [v for v in [tech_quizzes, gd_avg, interview_avg] if v > 0]
        tech_holistic_avg = sum(tech_modules) / len(tech_modules) if tech_modules else 0

        # 3. Level Up Logic
        new_apt_lvl = apt_lvl
        if apt_avg >= 7 and apt_lvl < 3:
            new_apt_lvl += 1
            
        new_tech_lvl = tech_lvl
        if tech_holistic_avg >= 7 and tech_lvl < 3:
            new_tech_lvl += 1

        level_up_occurred = (new_apt_lvl > apt_lvl or new_tech_lvl > tech_lvl)

        # 4. Save to weekly_stats
        overall_avg = (apt_avg + tech_holistic_avg) / 2 if (apt_avg > 0 and tech_holistic_avg > 0) else (apt_avg or tech_holistic_avg)
        
        db.execute(
            text("""
                INSERT INTO weekly_stats (username, week_start_date, avg_score, is_level_up, total_activities)
                VALUES (:u, :d, :s, :lu, :cnt)
            """),
            {
                "u": username,
                "d": today,
                "s": overall_avg,
                "lu": 1 if level_up_occurred else 0,
                "cnt": total_activities
            }
        )

        # 5. Update User Levels
        db.execute(
            text("""
                UPDATE users SET 
                aptitude_level = :al, 
                technical_level = :tl, 
                last_level_update = NOW() 
                WHERE username = :u
            """),
            {"al": new_apt_lvl, "tl": new_tech_lvl, "u": username}
        )
        
        db.commit()
        print(f"🌟 Weekly Level Up Processed for {username}. Level up: {level_up_occurred}")
        return level_up_occurred

    except Exception as e:
        print(f"❌ Error in weekly level up: {e}")
        db.rollback()
        return False

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
        return "Easy"
    elif level == 2:
        return "Medium"
    else:
        return "Hard"

def get_todays_questions(db: Session, username: str, category: str, target_branch: str = None):
    """Get 10 questions for today - avoiding repeats from previous days"""
    today = date.today()
    
    # If target_branch is provided and DOES NOT MATCH user's branch, do NOT cache/use daily_quiz
    # This is "Practice Mode"
    
    user_result = db.execute(
        text("SELECT branch FROM users WHERE username = :username"),
        {"username": username}
    )
    user_row = user_result.fetchone()
    user_actual_branch = user_row[0] if user_row else None

    is_practice_mode = False
    if category.lower() == "technical" and target_branch and target_branch != user_actual_branch:
        is_practice_mode = True
        print(f"🎯 Practice Mode: User {username} ({user_actual_branch}) practicing {target_branch}")
    
    # Check if user already has questions for today (ONLY if not practice mode)
    if not is_practice_mode:
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
            # Return existing question IDs, but VERIFY they still exist
            # This prevents returning fewer than 10 questions if some were deleted during updates
            try:
                id_list = [int(x) for x in existing[0].split(",")]
                placeholders = ",".join([str(x) for x in id_list])
                verify_result = db.execute(text(f"SELECT id FROM questions WHERE id IN ({placeholders})")).fetchall()
                verified_ids = [r[0] for r in verify_result]
                
                if len(verified_ids) == len(id_list) and len(verified_ids) >= 1:
                    return verified_ids
                else:
                    print(f"⚠️ Cache mismatch for {username}: {len(verified_ids)}/{len(id_list)} IDs found. Regenerating...")
            except Exception as e:
                print(f"⚠️ Error verifying cached IDs: {e}. Regenerating...")
    
    # Get all past questions to avoid repetition (Skip for practice mode to allow unlimited practice?)
    # Let's keep avoiding repetition for practice mode too to keep it fresh
    past_quizzes = db.execute(
        text("""
            SELECT question_ids FROM daily_quiz 
            WHERE username = :username 
            AND category = :category
        """),
        {"username": username, "category": category.lower()}
    ).fetchall()

    seen_ids = set()
    for row in past_quizzes:
        if row[0]:
            for qid in row[0].split(','):
                try:
                    seen_ids.add(int(qid))
                except ValueError:
                    pass

    # Get user level for difficulty
    difficulty = get_user_level(db, username, category)

    # Fetch ALL candidate questions for this category & difficulty
    if category.lower() == "technical":
        # Use target_branch if provided, otherwise user's actual branch
        branch_to_use = target_branch if target_branch else user_actual_branch
        
        if branch_to_use:
            # Fetch candidate questions where the requested branch is in the comma-separated branch list
            # We use FIND_IN_SET and REPLACE to handle possible spaces in the DB values
            candidates_result = db.execute(
                text("""
                    SELECT id FROM questions 
                    WHERE category = :category 
                    AND LOWER(difficulty) = LOWER(:difficulty)
                    AND (
                        LOWER(branch) = LOWER(:branch)
                        OR FIND_IN_SET(LOWER(:branch), REPLACE(LOWER(branch), ' ', ''))
                    )
                """),
                {"category": category.lower(), "difficulty": difficulty, "branch": branch_to_use.upper()}
            )
        else:
            # No branch set - return empty (user must select branch)
            candidates_result = db.execute(
                text("""
                    SELECT id FROM questions 
                    WHERE category = :category 
                    AND LOWER(difficulty) = LOWER(:difficulty)
                    AND 1=0
                """),
                {"category": category.lower(), "difficulty": difficulty}
            )
    else:
        # Aptitude/GD - pull 'Common' branch, empty string, or NULL branch questions
        candidates_result = db.execute(
            text("""
                SELECT id FROM questions 
                WHERE LOWER(category) = LOWER(:category) 
                AND LOWER(difficulty) = LOWER(:difficulty)
                AND (LOWER(branch) = 'common' OR branch IS NULL OR branch = '')
            """),
            {"category": category, "difficulty": difficulty}
        )

    
    all_candidate_ids = [row[0] for row in candidates_result.fetchall()]
    
    # FALLBACK: If fewer than 10 questions found for specific difficulty, try other difficulties for this branch/category
    if len(all_candidate_ids) < 10:
        print(f"🔍 Only {len(all_candidate_ids)} questions for {category} at {difficulty} level. Pulling from other difficulties...")
        
        if category.lower() == "technical" and branch_to_use:
            # Pull ALL questions for this branch regardless of difficulty
            fallback_result = db.execute(
                text("""
                    SELECT id FROM questions 
                    WHERE category = :category 
                    AND (
                        LOWER(branch) = LOWER(:branch)
                        OR FIND_IN_SET(LOWER(:branch), REPLACE(LOWER(branch), ' ', ''))
                    )
                """),
                {"category": category.lower(), "branch": branch_to_use.upper()}
            )
            all_candidate_ids = [row[0] for row in fallback_result.fetchall()]
        elif category.lower() != "technical":
            # For Aptitude/GD, pull all 'Common', empty, or NULL questions regardless of difficulty
            fallback_result = db.execute(
                text("""
                    SELECT id FROM questions 
                    WHERE LOWER(category) = LOWER(:category) 
                    AND (LOWER(branch) = 'common' OR branch IS NULL OR branch = '')
                """),
                {"category": category}
            )
            all_candidate_ids = [row[0] for row in fallback_result.fetchall()]

            
        print(f"✅ Total available questions for {category}: {len(all_candidate_ids)}")

    
    # Filter out seen questions
    available_ids = [qid for qid in all_candidate_ids if qid not in seen_ids]

    
    # Selection Logic
    question_ids = []
    
    if len(available_ids) >= 10:
        # We have enough new questions
        random.shuffle(available_ids)
        question_ids = available_ids[:10]
    else:
        # Not enough new questions, mix in some old ones or just take what we have + random repeats
        question_ids = available_ids[:] # Take all available new ones
        
        # Fill the rest with random old questions of same difficulty
        needed = 10 - len(question_ids)
        if needed > 0:
            # Re-use candidate_ids that ARE in seen_ids
            used_candidates = [qid for qid in all_candidate_ids if qid in seen_ids]
            random.shuffle(used_candidates)
            question_ids.extend(used_candidates[:needed])
            
    # Final check if we still don't have 10 (e.g. total questions < 10)
    if len(question_ids) < 10:
         # Try to fill with ANY questions from category if strictly needed, or just return what we have
         # For now, let's just return what we have if total universe is small
         pass

    if not question_ids:
         raise HTTPException(
            status_code=404, 
            detail=f"No questions available for {category} ({difficulty})."
        )
    
    # Save for today (ONLY if NOT practice mode)
    if not is_practice_mode:
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
        ans = str(row[6]).strip().upper() if row[6] else "A"
        questions_dict[row[0]] = {
            "id": row[0],
            "question": row[1],
            "options": [row[2], row[3], row[4], row[5]],
            "answer": ans, # Frontend expects 'answer'
            "correct_answer": ans,
            "area": row[7] or "General",
            "explanation": row[8] or "No explanation provided.",
            "difficulty": row[9]
        }



    
    # Return in original order
    return [questions_dict[id] for id in question_ids if id in questions_dict]

def generate_question_explanation(db: Session, question_id: int):
    """Generate and save an AI explanation using Groq (via ai_engine) if it's missing."""
    from ai_engine import enhance_question, parse_ai_response
    
    result = db.execute(
        text("SELECT question, option_a, option_b, option_c, option_d, correct_answer, explanation FROM questions WHERE id = :id"),
        {"id": question_id}
    )
    row = result.fetchone()
    if not row:
        return
    
    question_text, opt_a, opt_b, opt_c, opt_d, correct_answer_letter, current_exp = row
    
    # If explanation is missing or placeholder, generate a new one
    is_placeholder = (
        not current_exp or 
        len(current_exp.strip()) < 50 or
        current_exp == "No explanation provided." or 
        current_exp == "Explanation generation failed."
    )
    
    if is_placeholder:
        print(f"🤖 [Background] Generating AI explanation for Q{question_id} using Groq...")
        options_text = f"A: {opt_a}, B: {opt_b}, C: {opt_c}, D: {opt_d}"
        
        try:
            # Use ai_engine to get high-quality explanation
            raw_ai = enhance_question(question_id, question_text, options_text, correct_answer_letter)
            parsed = parse_ai_response(raw_ai)
            
            if parsed and parsed.get("explanation"):
                new_explanation = parsed["explanation"]
                db.execute(
                    text("""
                        UPDATE questions 
                        SET explanation = :exp, area = :area, difficulty_level = :dl, difficulty = :dt 
                        WHERE id = :id
                    """),
                    {
                        "exp": new_explanation, 
                        "area": parsed["area"],
                        "dl": parsed["difficulty_level"],
                        "dt": parsed["difficulty_text"],
                        "id": question_id
                    }
                )
                db.commit()
                print(f"✅ [Background] Saved Groq explanation for Q{question_id}")
        except Exception as e:
            print(f"⚠️ [Background] Groq failed for Q{question_id}: {e}")

def ensure_explanations_exist(question_ids: list):
    """Ensure all questions in the list have AI explanations in parallel (Background Task)."""
    def job(qid):
        db = SessionLocal()
        try:
            generate_question_explanation(db, qid)
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.map(job, question_ids)

def validate_answer(db: Session, question_id: int, user_answer: str):
    """
    Validate user answer and return explanation.
    """
    result = db.execute(
        text("SELECT correct_answer, explanation FROM questions WHERE id = :id"),
        {"id": question_id}
    )
    
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Question not found")
    
    correct_answer_letter, current_exp = row
    correct_answer_letter = correct_answer_letter.strip().upper()
    
    # If it's missing or clearly too short/placeholder, generate on the fly
    is_placeholder = (
        not current_exp or 
        len(current_exp.strip()) < 50 or
        current_exp == "No explanation provided." or 
        current_exp == "Explanation generation failed."
    )
    
    if is_placeholder:
        print(f"🤖 [Auto-Refining] Triggering explanation generation for Q{question_id}")
        generate_question_explanation(db, question_id)
        # Fetch updated explanation
        result = db.execute(text("SELECT explanation FROM questions WHERE id = :id"), {"id": question_id})
        current_exp = result.fetchone()[0]

    user_answer = user_answer.strip().upper()
    is_correct = (user_answer == correct_answer_letter)
    
    return is_correct, correct_answer_letter, current_exp or "No explanation provided."

# --- FASTAPI SETUP ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "="*70)
    print("PLACEMENT APP - STARTING UP")
    print("="*70)
    
    try:
        with engine.connect() as conn:
            print("Database connection successful!")
        
        # Initialize DB tables
        init_db()
        print("Database tables initialized")

        # Initialize Whisper model
        print("Loading Whisper model...")
        global stt_model
        stt_model = whisper.load_model("base")
        print("Whisper model loaded!")
        
    except Exception as e:
        print(f"Startup Failed: {e}")
        traceback.print_exc()
        raise e
    
    print("\nFeatures enabled:")
    print("   - Adaptive Quiz System (10 questions/day)")
    print("   - Progressive Difficulty")
    print("   - Interview Practice")
    print("   - Performance Analytics")
    
    print("\nAPI Documentation:")
    print("   Swagger UI: http://localhost:8000/docs")
    print("\n" + "="*70 + "\n")
    
    yield
    
    print("\nShutting down gracefully...")

app = FastAPI(
    title="Placement Preparation Platform",
    description="AI-Powered Placement Prep with Adaptive Quiz System",
    version="4.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# Import and include routers
from teacher_routes import router as teacher_router
from gd import router as gd_router
from news_routes import router as news_router

app.include_router(teacher_router)
app.include_router(gd_router, prefix="/gd_module", tags=["GD Module"])
app.include_router(news_router)

# --- ROUTES ---

@app.post("/register", tags=["Authentication"])
async def register(user: UserAuth, db: Session = Depends(get_db)):
    """Register a new user"""
    from models import User
    try:
        existing = db.query(User).filter(User.username == user.username.strip()).first()
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")
        
        # Explicitly assign branch and other fields
        new_user = User()
        new_user.username = user.username.strip()
        new_user.password_hash = user.password
        new_user.aptitude_level = 1
        new_user.technical_level = 1
        new_user.branch = user.branch
        new_user.role = user.role.lower() if user.role else 'student'
        
        db.add(new_user)
        db.commit()
        return {"status": "success", "message": "User registered successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login", tags=["Authentication"])
async def login(user: UserAuth, db: Session = Depends(get_db)):
    """Login user"""
    try:
        result = db.execute(
            text("SELECT username, password_hash FROM users WHERE username = :username"),
            {"username": user.username.strip()}
        )
        row = result.fetchone()
        
        if row and row[1] == user.password:
            # Trigger weekly level up check on login
            process_weekly_level_up(user.username.strip(), db)
            return {"status": "success", "username": row[0]}
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update_branch", tags=["User"])
async def update_branch(request: UpdateBranchRequest, db: Session = Depends(get_db)):
    """Update user's branch after registration"""
    from models import User
    try:
        user = db.query(User).filter(User.username == request.username.strip()).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.branch = request.branch
        
        # Clear technical quiz cache for this user so they get correct branch questions immediately
        print(f"🗑️ Clearing technical quiz cache for user: {request.username.strip()}")
        result = db.execute(
            text("DELETE FROM daily_quiz WHERE username = :username AND category = 'technical'"),
            {"username": request.username.strip()}
        )
        print(f"✅ Cache cleared. Rows affected: {result.rowcount}")
        
        db.commit()
        return {"status": "success", "message": f"Branch updated to {request.branch}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_daily_quiz", tags=["Quiz System"])
async def get_daily_quiz(request: QuizRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Get today's 10 questions
    - Same questions for entire day
    - Resets at midnight
    """
    try:
        question_ids = get_todays_questions(db, request.username, request.category, request.target_branch)
        
        # Proactively generate explanations for any questions that lack them
        background_tasks.add_task(ensure_explanations_exist, question_ids)
        
        questions = get_questions_by_ids(db, question_ids)
        
        # Send full details to frontend
        
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

@app.post("/check_answer", tags=["Quiz System"])
async def check_answer(submission: AnswerSubmission, db: Session = Depends(get_db)):
    """Check a single answer - returns immediate feedback"""
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

@app.post("/submit_quiz", tags=["Quiz System"])
async def submit_quiz(submission: QuizCompleteSubmission, db: Session = Depends(get_db)):
    """
    Submit completed quiz
    - Updates user level if score >= 70%
    """
    try:
        percentage = (submission.score / submission.total_questions) * 100
        
        # Determine if this is practice mode
        user_result = db.execute(
            text("SELECT branch FROM users WHERE username = :username"),
            {"username": submission.username}
        )
        user_row = user_result.fetchone()
        user_branch = user_row[0] if user_row else None
        
        is_practice_mode = False
        if submission.target_branch and submission.target_branch != user_branch and submission.category.upper() == "TECHNICAL":
            is_practice_mode = True
            print(f"🎯 Practice Mode Submission: Score not saved for {submission.username}")
        
        # Save result (ONLY if NOT practice mode)
        if not is_practice_mode:
            # Use provided weak area or default to "Daily Quiz"
            area_to_save = submission.weak_area if submission.weak_area else "Daily Quiz"
            
            db.execute(
                text("""
                    INSERT INTO results (username, category, score, area, timestamp) 
                    VALUES (:username, :category, :score, :area, NOW())
                """),
                {
                    "username": submission.username,
                    "category": submission.category.upper(),
                    "score": submission.score,
                    "area": area_to_save
                }
            )
            
            # Level up logic removed from here (now weekly on Sundays)
            # Threshold was 70%, but we aggregate holistically now.
            level_up = False 
            
            db.commit()

            
            return {
                "status": "success",
                "score": submission.score,
                "total": submission.total_questions,
                "percentage": round(percentage, 1),
                "level_up": level_up,
                "message": "Great job! Level up!" if level_up else "Keep practicing!"
            }
        else:
             return {
                "status": "success",
                "score": submission.score,
                "total": submission.total_questions,
                "percentage": round(percentage, 1),
                "level_up": False,
                "message": f"Practice complete for {submission.target_branch}!"
            }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/quiz_status/{username}/{category}", tags=["Quiz System"])
async def get_quiz_status(username: str, category: str, db: Session = Depends(get_db)):
    """Check if user has already taken today's quiz"""
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
        
        return {
            "has_quiz_today": has_quiz_today,
            "current_level": difficulty,
            "date": str(today)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/weekly_report/{username}", tags=["Analytics"])
async def get_weekly_report(username: str, db: Session = Depends(get_db)):
    """Get performance analytics from weekly_stats"""
    try:
        # 1. Try to get historical weekly stats for the graph
        stats_result = db.execute(
            text("""
                SELECT avg_score, week_start_date FROM weekly_stats 
                WHERE username = :username 
                ORDER BY week_start_date ASC
            """),
            {"username": username.strip()}
        )
        stats_rows = stats_result.fetchall()
        
        # 2. If no weekly stats yet, fallback to raw results for recent trend
        if not stats_rows:
            raw_result = db.execute(
                text("""
                    SELECT score, timestamp FROM results 
                    WHERE username = :username 
                    ORDER BY timestamp DESC LIMIT 7
                """),
                {"username": username.strip()}
            )
            raw_rows = raw_result.fetchall()
            if not raw_rows:
                return {"has_data": False}
            
            graph_data = [{"score": r[0], "time": str(r[1])} for r in raw_rows]
            graph_data.reverse()
        else:
            graph_data = [{"score": r[0], "time": str(r[1].date())} for r in stats_rows]

        # 3. Calculate latest performance metrics
        latest_avg = graph_data[-1]["score"] if graph_data else 0
        
        status = "Beginner"
        if latest_avg >= 8:
            status = "Expert"
        elif latest_avg >= 5:
            status = "Intermediate"

        return {
            "has_data": True,
            "graph_data": graph_data,
            "status": status,
            "current_performance": round(latest_avg, 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard/{username}", tags=["User"])
async def get_dashboard(username: str, db: Session = Depends(get_db)):
    """Get user dashboard data"""
    from models import User, Score
    try:
        user = db.query(User).filter(User.username == username.strip()).first()
        
        if user:
            # Trigger weekly level up check on dashboard view
            process_weekly_level_up(username.strip(), db)
            
            # Get latest weak area
        latest_result = db.query(Score).filter(Score.username == username.strip()).order_by(Score.id.desc()).first()
        weak_area = latest_result.area if latest_result and latest_result.area else "None"

        if user:
            # Get latest weak area for Technical
            tech_result = db.query(Score).filter(
                Score.username == username.strip(), 
                Score.category == "TECHNICAL"
            ).order_by(Score.id.desc()).first()
            weak_area_tech = tech_result.area if tech_result and tech_result.area else "None"

            # Get latest weak area for Aptitude
            apt_result = db.query(Score).filter(
                Score.username == username.strip(), 
                Score.category == "APTITUDE"
            ).order_by(Score.id.desc()).first()
            weak_area_apt = apt_result.area if apt_result and apt_result.area else "None"

            return {
                "id": user.id,
                "username": user.username,
                "aptitude_level": user.aptitude_level,
                "technical_level": user.technical_level,
                "branch": user.branch,
                "weak_area_tech": weak_area_tech,
                "weak_area_apt": weak_area_apt
            }
        raise HTTPException(status_code=404, detail="User not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate_interview", tags=["Interview Practice"])
async def evaluate(audio: UploadFile = File(...), username: str = Form("Anonymous"), db: Session = Depends(get_db)):

    """Evaluate interview audio response"""
    temp_filename = f"temp_{audio.filename}"
    try:
        with open(temp_filename, "wb") as f:
            f.write(await audio.read())
        
        transcription_result = stt_model.transcribe(temp_filename)
        transcription = transcription_result.get("text", "").strip()

        prompt = f"""
System: You are a strict Technical Interviewer.
Candidate's Answer: "{transcription}"
Question: "Explain final vs const in Dart."

Evaluate strictly. Return ONLY JSON:
{{
  "score": "X/10",
  "feedback": "Direct, honest feedback.",
  "ideal_answer": "Professional explanation."
}}
"""
        
        response = ollama.generate(model='llama3', prompt=prompt, format='json') 
        data = json.loads(response['response'])
        
        # Extract numeric score (e.g., "7/10" -> 7)
        score_val = 5 # default
        if 'score' in data:
            match = re.search(r'(\d+)', str(data['score']))
            if match:
                score_val = int(match.group(1))

        # Persist the score to the results table
        db.execute(
            text(
                """
                INSERT INTO results (username, score, category, area, timestamp)
                VALUES (:username, :score, :category, :area, :timestamp)
                """
            ),
            {
                "username": username,
                "score": score_val,
                "category": "INTERVIEW",
                "area": "Interview Practice", # Default area for interview
                "timestamp": datetime.now()
            }
        )
        db.commit()

        return {
            "status": "success",
            "score": data.get("score", "5/10"),
            "feedback": data.get("feedback", ""),
            "ideal_answer": data.get("ideal_answer", "")
        }

    except Exception as e:
        db.rollback() # Rollback in case of error during DB operation
        return {"error": str(e)}
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

@app.get("/", tags=["Root"])
def root():
    return {
        "app": "Placement Preparation Platform",
        "version": "4.0.0",
        "database": "MySQL",
        "features": {
            "adaptive_quiz": "10 questions daily with progressive difficulty",
            "answer_validation": "Fixed - accurate checking",
            "level_system": "Auto-level up at 70% score",
            "interview_practice": "Voice-based AI evaluation",
            "analytics": "Performance tracking"
        },
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)