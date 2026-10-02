# 🧠 AI Career Intelligence Platform

A production-ready AI-powered career intelligence platform with resume analysis, ATS scoring, job matching, and a multi-agent RAG career advisor.

## ✨ Features

- **Resume ATS Analyzer** — Upload PDF/DOCX, get detailed scoring, keyword analysis, and improvement tips
- **AI Job Matcher** — Smart job recommendations matched to your skills
- **Career Advisor** — Multi-agent LangGraph + RAG pipeline powered by Google Gemini
- **User Authentication** — JWT-based auth with refresh tokens

## 🏗️ Architecture

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI + Python 3.12 |
| Frontend | Next.js 16 + TypeScript + Tailwind CSS |
| Database | PostgreSQL 16 (async via asyncpg + SQLAlchemy) |
| AI/LLM | Google Gemini 2.0 Flash |
| Vector DB | ChromaDB (embedded) |
| Agents | LangGraph multi-agent workflow |
| Auth | JWT (python-jose) + bcrypt |

---

## 🚀 Deploy to Production

### Option A: Render.com (Recommended — Free Tier)

**Step 1: Deploy Backend + PostgreSQL**

1. Go to [https://render.com](https://render.com) and sign in with GitHub
2. Click **+ New** → **Blueprint**
3. Connect your GitHub repo: `vdeekshith2007/AI-career-intelligence-application`
4. Render will auto-detect `render.yaml` and create:
   - ✅ PostgreSQL database (`ai-career-db`)
   - ✅ Backend API service (`ai-career-backend`)
5. Set these environment variables in the Render dashboard for the backend service:
   | Variable | Value |
   |----------|-------|
   | `GEMINI_API_KEY` | Your key from [aistudio.google.com](https://aistudio.google.com/app/apikey) |
   | `CORS_ORIGINS` | `["https://YOUR-APP.vercel.app"]` (fill in after Step 2) |
   | `ADMIN_EMAIL` | `your-email@example.com` |
6. Click **Create Resources** — wait ~10 minutes for first build
7. Copy the backend URL (e.g. `https://ai-career-backend-xxxx.onrender.com`)

**Step 2: Deploy Frontend to Vercel**

1. Go to [https://vercel.com](https://vercel.com) and sign in with GitHub
2. Click **Add New** → **Project**
3. Import `vdeekshith2007/AI-career-intelligence-application`
4. Set **Root Directory** to `frontend`
5. Add environment variable:
   | Variable | Value |
   |----------|-------|
   | `NEXT_PUBLIC_API_URL` | `https://ai-career-backend-xxxx.onrender.com/api/v1` |
6. Click **Deploy** — wait ~3 minutes
7. Copy the Vercel URL (e.g. `https://ai-career-app.vercel.app`)

**Step 3: Update CORS on Backend**

Go back to Render → Backend service → Environment → update `CORS_ORIGINS`:
```
["https://ai-career-app.vercel.app"]
```
Click **Save Changes** → Render redeploys automatically.

---

### Option B: Railway.app (One-click)

1. Go to [https://railway.app](https://railway.app)
2. Click **New Project** → **Deploy from GitHub repo**
3. Select `vdeekshith2007/AI-career-intelligence-application`
4. Railway detects `railway.toml`
5. Add a **PostgreSQL** plugin from the Railway dashboard
6. Set environment variables:
   - `DATABASE_URL` — auto-provided by Railway PostgreSQL plugin
   - `SECRET_KEY` — generate: `python -c "import secrets; print(secrets.token_hex(32))"`
   - `GEMINI_API_KEY` — from Google AI Studio
   - `CORS_ORIGINS` — your frontend URL

---

## 💻 Local Development

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker + WSL2 (for PostgreSQL container)

### Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/vdeekshith2007/AI-career-intelligence-application.git
cd AI-career-intelligence-application

# 2. Start everything (PostgreSQL + Backend + Frontend)
npm run dev
```

Or double-click `start_dev.bat` on Windows.

Open http://localhost:3000

### Manual Setup

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**PostgreSQL (via Docker):**
```bash
docker compose up -d db
```

---

## ⚙️ Environment Variables

### Backend

Copy `backend/.env.production.template` to `backend/.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | 32+ char random string |
| `DATABASE_URL` | ✅ | PostgreSQL connection URL |
| `GEMINI_API_KEY` | ⚠️ Optional | Enables AI features (falls back to local synthesis) |
| `CORS_ORIGINS` | ✅ | JSON array of frontend URLs |
| `ADMIN_EMAIL` | ✅ | Admin user email |
| `ADMIN_PASSWORD` | ✅ | Admin user password (secure) |

### Frontend

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API base URL (e.g. `https://your-backend.onrender.com/api/v1`) |

---

## 🔍 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/auth/register` | Register user |
| POST | `/api/v1/auth/login` | Login + JWT |
| GET | `/api/v1/auth/me` | Get profile |
| POST | `/api/v1/resumes/upload` | Upload resume |
| POST | `/api/v1/resumes/{id}/analyze` | ATS analysis |
| GET | `/api/v1/jobs/recommendations` | AI job matching |
| POST | `/api/v1/chat/sessions` | Start chat session |
| POST | `/api/v1/chat/sessions/{id}/messages` | Send message |

API Docs (dev only): http://localhost:8000/docs

---

## 📋 System Requirements

| Service | Min Specs |
|---------|-----------|
| Backend | 512MB RAM, 0.5 CPU |
| Frontend | 256MB RAM |
| PostgreSQL | 512MB storage |

---

## 🔒 Security

- All passwords hashed with bcrypt
- JWT RS256 signing with configurable expiry
- Security headers middleware (HSTS, CSP, X-Frame-Options)
- CORS whitelist enforced in production
- No secrets committed to Git