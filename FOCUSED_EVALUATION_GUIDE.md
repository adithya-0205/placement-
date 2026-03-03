# Focused Project Guide: 4 Core Pillars

This guide focuses exclusively on the core modules of your platform: **Aptitude, Technical, News, and Teacher Dashboard**.

---

## 🏗 1. Aptitude & Technical Quizzes
These modules handle the adaptive learning and student assessment.

### Code Highlights: `backend/main.py` & `adaptive_quiz.py`
- **Quiz Fetching**:
  ```python
  @router.get("/quiz/{category}/{branch}/{username}")
  def get_daily_quiz(category, branch, username):
      # Fetches 10 questions based on Category (APTITUDE or TECHNICAL)
      # and Branch (CSE, MECH, etc.). It filters by the user's current 'technical_level'.
  ```
- **Adaptive Leveling**:
  ```python
  def process_weekly_level_up():
      # Runs every Sunday. 
      # Logic: Average Score > 7.5 -> Level Up.
  ```

### Key Logic for Evaluators:
*   **Aptitude**: Questions are common across all branches but vary by difficulty.
*   **Technical**: Questions are specific to the student's selected branch (CSE/AIDS/CSBS/MECH/ECE/EEE).
*   **AI Explanations**: Uses **Llama 3.1** via Ollama to generate step-by-step solutions for every question.

---

## 📰 2. Industry News & AI Summarization
Keeps students updated with tech trends using raw data and AI processing.

### Code Highlights: `backend/news_routes.py`
- **Parallel Fetching**:
  ```python
  with ThreadPoolExecutor(max_workers=20) as executor:
      raw_items = list(executor.map(fetch_story, top_ids))
  ```
- **AI Summary**:
  ```python
  prompt = f"Summarize this tech news title... for a student's placement preparation: '{request.title}'"
  ```

### Key Logic for Evaluators:
*   **Real-time Data**: Fetched live from Hacker News.
*   **Ollama Integration**: Summaries are generated only when the user clicks "Read Summary" to save server resources.
*   **TTS**: Flutter uses the `flutter_tts` package to vocalize the summary.

---

## 📊 3. Teacher Dashboard
Allows faculty to monitor progress and manage question datasets.

### Code Highlights: `backend/teacher_routes.py`
- **Aggregate Analytics**:
  ```python
  @router.get("/teacher/analytics/{branch}")
  def get_branch_analytics(branch):
      # Calculates the average score of all students in a branch.
      # Identifies "Weak Topics" across the entire class.
  ```
- **Data Import**:
  ```python
  @router.post("/teacher/upload_questions")
  def upload_csv(file: UploadFile):
      # Parses CSV files and bulk-inserts them into the MySQL 'questions' table.
  ```

### Key Logic for Evaluators:
*   **Data-Driven Teaching**: Helps teachers see which topics (e.g., "Data Structures") the entire class is struggling with.
*   **Scalability**: Supports thousands of questions across multiple engineering departments.

---

## ❓ FAQ for the 4 Pillars

**Q: How do you identify a student's weak area?**
*A: We track the 'topic' field for every incorrect answer. The topic with the highest failure rate is flagged as the "Weak Area" on the Dashboard.*

**Q: Why use local AI (Ollama) instead of ChatGPT API?**
*A: For student data privacy and to maintain the project with zero operational costs. It runs entirely on the college/local server.*

**Q: How is the Teacher Dashboard secured?**
*A: It uses JWT (JSON Web Token) authentication to ensure only users with the 'teacher' role can access analytics and upload questions.*
