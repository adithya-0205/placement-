# 75% Evaluation Technical Presentation Guide

This document provides a detailed breakdown of the AI Placement Assistant project. It is designed to help you explain the "why" and "how" of every major component during your evaluation.

## 1. Project Overview & Architecture
The project is an **AI-driven career preparation platform** that helps students prepare for placements using Technical/Aptitude quizzes, AI Group Discussions, and real-time Industry Insights.

### The Tech Stack
- **Frontend**: Flutter (Cross-platform UI)
- **Backend**: FastAPI (High-performance Python API)
- **AI Engines**: 
  - **Ollama (Llama 3.1)**: Generates quiz explanations and news summaries.
  - **OpenAI Whisper**: Transcribes audio for Interview/GD practice.
- **Database**: MySQL (Structured data management)
- **State Management**: Provider (Flutter)

---

## 2. Backend Deep Dive (FastAPI)

### `backend/main.py` (The Brain)
- **Purpose**: Initializes the server, handles authentication, and orchestrates the Quiz system.
- **Key Logic**:
  - `lifespan`: Loads the Whisper model once at startup to save memory.
  - `get_daily_quiz`: An adaptive algorithm that fetches 10 questions per day based on the user's difficulty level and branch.
  - `process_weekly_level_up`: Runs every Sunday to analyze student performance and "Level Up" their difficulty setting (Adaptive Learning).

### `backend/news_routes.py` (Real-time Insights)
- **Purpose**: Fetches technology trends from Hacker News and summarizes them using AI.
- **Key Logic**:
  - `get_latest_news`: Uses a `ThreadPoolExecutor` to fetch 80 stories in parallel for maximum speed.
  - `get_news_summary`: Takes a news title and sends a prompt to **Llama 3.1** to create a one-sentence professional summary.

### `backend/ai_engine.py` (AI Logic)
- **Purpose**: Contains the raw prompts and configurations for the LLM.
- **Logic**: It structures instructions so the AI acts like a "Placement Expert" rather than a general chatbot.

---

## 3. Frontend Deep Dive (Flutter)

### `frontend/lib/screens/dashboard_screen.dart` (The Nerve Center)
- **Purpose**: Central hub for students. Shows progress charts and the news popup.
- **Key Logic**:
  - `Timer.periodic`: Triggers the industry news popup every 5 minutes.
  - `OverlayEntry`: Used to "inject" the news notification on top of the UI without interrupting the user's workflow.
  - `LineChart`: Visualizes weekly progress using the `fl_chart` library.

### `frontend/lib/widgets/news_notification.dart` (Dynamic UI)
- **Purpose**: The sliding card that shows latest tech news.
- **Logic**: Uses `AnimationController` for the smooth slide-in effect and `FlutterTts` to read summaries aloud when the user clicks "Read".

### `frontend/lib/api_config.dart` (The Bridge)
- **Purpose**: Centralizes all HTTP communication.
- **Logic**: All frontend requests go through this class, making it easy to change the server address (localhost to IP) in one place.

---

## 4. Demonstration Script (75% Evaluation)

Follow these steps for a "WOW" demo:

1.  **Login & Dashboard**: Show the personalized greeting and the **Weekly Holistic Growth** graph. Explain how it tracks progress across all modules.
2.  **Industry Trends**: Navigate to the news section. Explain that the data is live technology news. Highlight the **AI Summarization** by clicking the volume icon.
3.  **Quiz Flow**: Start a Technical Quiz. Answer a question and show the **AI Explanation**. Explain that the AI clarifies *why* an answer is correct.
4.  **GD/Interview**: Demonstrate audio recording. Mention that **Whisper AI** transcribes the voice and **Llama 3.1** evaluates the content quality.

---

## 5. Potential Evaluator Questions & Answers

**Q: How does the app decide the difficulty level?**
*A: Every Sunday, the backend calculates an average score. If it's >7/10, the user's level (Easy/Medium/Hard) increments.*

**Q: Is the AI running locally?**
*A: Yes, we use Ollama to run high-performance models locally on the server, ensuring privacy and no API costs.*

**Q: Why use Flutter and FastAPI?**
*A: Flutter provides a premium, responsive UI, while FastAPI is the fastest Python framework for handling AI and data processing.*
