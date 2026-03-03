# 75% Evaluation: Potential Q&A Guide

Prepare for your evaluation by reviewing these likely questions from your project guide. The answers are tailored to your specific implementation.

---

## 🏗 Category 1: Architecture & Tech Stack

**Q1: Why did you choose FastAPI over Flask or Django?**
*   **Answer**: FastAPI is designed for high performance and handles asynchronous (`async/await`) operations natively. This is crucial for our project because we deal with long-running tasks like AI generation and voice transcription. It also automatically generates interactive API documentation (Swagger), which made testing easier.

**Q2: How does the Frontend (Flutter) communicate with the Backend (FastAPI)?**
*   **Answer**: We use RESTful APIs. The Flutter app sends HTTP requests (GET/POST) to specific endpoints on the FastAPI server. We use JSON as the data exchange format, ensuring the data is lightweight and easy to parse on both ends.

---

## 🤖 Category 2: AI & Machine Learning

**Q3: Which AI models are you using, and are they running on the cloud?**
*   **Answer**: We are using **Llama 3.1** for text generation (quizzes and summaries) and **OpenAI Whisper** for voice transcription. Crucially, these are running **locally** using the Ollama and Whisper libraries. This ensures complete data privacy and zero API costs.

**Q4: How do you handle the "hang" or delay when the AI is generating a response?**
*   **Answer**: We implement two strategies:
    1.  **Background Tasks**: On the backend, we move heavy AI tasks to background threads so the API response isn't blocked.
    2.  **Optimized Routes**: We use standard synchronous `def` for AI routes in FastAPI, allowing the server to manage them in a specialized thread pool without freezing the main event loop.

---

## 📊 Category 3: Database & Logic

**Q5: How does your Adaptive Quiz logic work?**
*   **Answer**: The backend tracks every student's performance in the `user_progress` table. Every Sunday, a maintenance script calculates their average score. If they consistently score above 75%, their `technical_level` is incremented in the `Students` table, and the quiz engine automatically fetches harder questions for them.

**Q6: What happens if the internet goes down? Can the app work?**
*   **Answer**: The frontend requires an active connection to talk to the local backend server. However, because our AI models (Ollama/Whisper) are hosted locally on our own server (your laptop in this case), we don't need external internet access for the AI features once the models are downloaded.

---

## 📱 Category 4: Frontend (Flutter)

**Q7: How do you manage the state of the user (login status) in Flutter?**
*   **Answer**: We use the **Provider** pattern. It allows us to maintain a global `AuthProvider` state. When a user logs in, the provider notifies all widgets to update the UI (like changing the "Login" button to a "Profile" icon) instantly without manual reloading.

**Q8: What is an 'OverlayEntry' and why did you use it for news?**
*   **Answer**: An `OverlayEntry` allows us to "float" a widget (the news notification) on top of all other screens. We used it for the periodic news popup so it can appear independently of which page the student is currently on, ensuring they never miss an update.

---

## 🛠 Category 5: Practical Challenges

**Q9: What was the biggest technical challenge you faced?**
*   **Answer**: The biggest challenge was integrating real-time Text-to-Speech (TTS) with AI summaries. We had to ensure the AI summary was generated first, then passed to the TTS engine without causing a UI "jerk" or crash. We solved this by using `Future` builders and asynchronous handling in Flutter.

**Q10: What is the roadmap for the final 25% of the project?**
*   **Answer**: For the final evaluation, we plan to:
    1.  Refine the UI for the Teacher's Dashboard.
    2.  Add more extensive datasets for AIDS and CSBS branches.
    3.  Implement a mock interview "video" simulation if hardware allows.
