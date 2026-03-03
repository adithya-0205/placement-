# AI Placement Assistant: Complete Project Documentation

This document provides a comprehensive breakdown of the entire system architecture, explaining every major file and its role in the project. Use this for your 75% evaluation to demonstrate a deep understanding of the codebase.

---

## 🏗 System Architecture
The system follows a **Client-Server Architecture**:
1.  **Frontend (Flutter)**: A reactive UI that communicates with the backend via REST APIs.
2.  **Backend (FastAPI)**: A high-performance Python server that handles data, AI logic, and external integrations.
3.  **Database (MySQL)**: Stores user profiles, quiz questions, performance metrics, and daily stats.
4.  **AI Layer (Ollama/Whisper)**: Local AI models for real-time natural language processing.

---

## 🟢 BACKEND EXPLANATION (Python/FastAPI)

### 1. `main.py` (The Central Hub)
*   **Role**: Initializes the FastAPI app, manages authentication, and controls the core quiz logic.
*   **Key Functions**:
    *   `lifespan`: Runs at startup; it pre-loads the Whisper model (`stt_model`) into GPU/RAM memory so it doesn't have to reload for every request.
    *   `get_daily_quiz`: This is our adaptive learning engine. It ensures every user gets 10 fresh questions every day filtered by their **Branch** (CSE/MECH/ECE) and **Difficulty Level**.
    *   `submit_quiz_results`: Saves scores and calculates the student's mastery of specific topics.

### 2. `news_routes.py` (Industry Trends)
*   **Role**: Handles third-party API integration and AI-based information distillation.
*   **Key Functions**:
    *   `get_latest_news`: Uses a `ThreadPoolExecutor` to fetch top stories from Hacker News in parallel. This keeps the UX fast.
    *   `get_news_summary`: Our AI-powered feature. It takes a raw headline and asks **Llama 3.1** to summarize it into a professional tip for students.

### 3. `gd.py` & `gd_evaluator.py` (Group Discussion Module)
*   **Role**: These files manage the AI-led mock group discussions.
*   **Key Logic**:
    *   It uses **Whisper AI** to transcribe the student's voice input.
    *   The `gd_evaluator` sends the transcription to Llama 3.1, which critiques the student's communication skills, confidence, and subject matter knowledge.

### 4. `database.py` (Data Layer)
*   **Role**: Manages the connection pool to MySQL.
*   **Key Code**:
    *   `get_db_connection`: Uses `mysql.connector.pooling` to manage multiple simultaneous database threads safely.

### 5. `ai_engine.py` (The AI Expert)
*   **Role**: Defines the "Personality" of the system.
*   **Key Logic**:
    *   Contains the system prompts that tell the AI it is a "Placement Coordinator." This ensures the generated summaries and quiz explanations are professional and helpful.

---

## 🔵 FRONTEND EXPLANATION (Flutter/Dart)

### 1. `lib/main.dart` (The Entry Point)
*   **Role**: Sets up the app's theme and state management.
*   **Key Logic**:
    *   Wraps the app in a `ChangeNotifierProvider`, making the `AuthProvider` (and user session) accessible to every screen in the app.

### 2. `lib/api_config.dart` (The API Service)
*   **Role**: Centralized communication layer.
*   **Key Logic**:
    *   Contains static methods like `fetchLatestNews()` and `evaluateInterview()`. This abstracts the complex `http` calls away from the UI code.

### 3. `lib/screens/dashboard_screen.dart` (Dashboard & Sidebar)
*   **Role**: The main interface showing progress charts and the news popup.
*   **Key Logic**:
    *   `_startNewsTimer()`: A periodic timer that triggers a news popup every 5 minutes from the right side of the screen.
    *   `LineChart`: Uses the `fl_chart` library to visualize the user's weekly performance.

### 4. `lib/screens/quiz_screen.dart` (Interactive Learning)
*   **Role**: Manages the quiz experience.
*   **Key Logic**:
    *   Implements a **30-second countdown timer** for each question.
    *   Displays **AI-generated explanations** immediately after a student submits their answer, providing instant feedback.

### 5. `lib/widgets/news_notification.dart` (Popup Widget)
*   **Role**: A dynamic overlay notification.
*   **Key Logic**:
    *   Uses `FlutterTts` (Text-to-Speech) to read summaries aloud, making the app more accessibility-friendly and engaging.

---

## 🛠 Project Highlights for Evaluators

1.  **Adaptive Learning**: The backend Sunday routine analyzes performance and automatically increases or decreases user difficulty level.
2.  **Locally Hosted AI**: We use **Ollama** and **Whisper** locally. This means ZERO costs for API keys and complete data privacy for user voice recordings.
3.  **Real-Time Data**: The "Industry Trends" feature ensures students are not just studying theory but are also aware of current market shifts.
4.  **Premium UI**: Custom animations, glassmorphism designs, and floating overlays create a high-quality user experience.
