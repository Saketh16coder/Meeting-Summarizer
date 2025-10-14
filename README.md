

# 🧠 Meeting Summarizer

A simple **AI-powered Meeting Summarizer** built with **FastAPI**, **OpenAI Whisper**, and **GPT-3.5**.  
It allows users to upload meeting audio files, automatically transcribe them, summarize discussions, and store transcripts locally in an SQLite database.

---

## 🚀 Features
- 🎤 **Audio Upload** – Supports `.wav`, `.mp3`, `.m4a` and other formats  
- 🧾 **Automatic Transcription** – Uses **OpenAI Whisper (whisper-1)**  
- 🧠 **Summarization** – Uses **GPT-3.5-Turbo** to generate:
  - Title and short summary  
  - Key decisions  
  - Action items (task, assignee, due date, rationale)  
- 💾 **Local Storage** – Stores transcripts and summaries in `meetings.db`  
- 🔎 **Saved Meeting Viewer** – Easily view previously uploaded meetings  

---

## 🗂️ Project Structure
📦 Meeting-Summarizer
├── main.py # FastAPI backend
├── index.html # Frontend UI
├── requirements.txt # Dependencies
├── meetings.db # Auto-created SQLite database
└── README.md


---

## ⚙️ Setup & Installation

### 1️⃣ Clone the repository
```bash
git clone https://github.com/<your-username>/Meeting-Summarizer.git
cd Meeting-Summarizer

### 2️⃣ Create a virtual environment
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# OR
.venv\Scripts\activate          # Windows

### 3️⃣ Install dependencies
pip install -r requirements.txt

### 4️⃣ Add your OpenAI API key
Create a .env file in the project root:
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

▶️ Run the App
Start the FastAPI server:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
Then open in your browser: http://127.0.0.1:8000

Upload an audio file and wait for the summarized output to appear.


### 🧩 API Endpoints

| Method | Endpoint             | Description                                 |
| ------ | -------------------- | ------------------------------------------- |
| `GET`  | `/`                  | Serves the main HTML interface              |
| `POST` | `/upload`            | Uploads and summarizes a meeting audio file |
| `GET`  | `/api/meetings`      | Lists recent saved meetings                 |
| `GET`  | `/api/meetings/{id}` | Retrieves one meeting record                |
| `GET`  | `/health`            | Health check                                |

### 💾 Database Schema (SQLite)

| Column           | Type    | Description               |
| ---------------- | ------- | ------------------------- |
| `id`             | INTEGER | Primary key               |
| `filename`       | TEXT    | Uploaded file name        |
| `transcript`     | TEXT    | Transcribed text          |
| `title`          | TEXT    | Meeting title             |
| `summary`        | TEXT    | Short summary             |
| `decisions_json` | TEXT    | JSON list of decisions    |
| `actions_json`   | TEXT    | JSON list of action items |
| `notes`          | TEXT    | Full raw LLM output       |
| `created_at`     | TEXT    | Timestamp (UTC)           |


🧠 Example Output

Summary:

Discussed release timeline. Decided to finish feature X by next Friday.
Action item: Bob to complete documentation.


Action Items:
| Task                | Assignee | Due Date    | Rationale               |
| ------------------- | -------- | ----------- | ----------------------- |
| Write documentation | Bob      | Next Friday | Docs needed for release |

🛠️ Technologies Used

Python 3.10+
FastAPI
SQLite
OpenAI Whisper (Audio Transcription)
GPT-3.5-Turbo (Summarization)
HTML + JS (Frontend)

📋 Notes
The meetings.db file will be auto-created in the root directory.
If the API key is missing, the app will show "OPENAI_API_KEY not set" errors.
For testing without API key, a mock mode can be added easily.

🧑‍💻 Author
Saketh
Built as a learning project on AI meeting summarization using Whisper and GPT models.
