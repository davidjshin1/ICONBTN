# UNGODLY UI Asset Generator - Deployment Guide

This guide walks you through deploying the UNGODLY Asset Generator to Railway for public access.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Railway                               │
│  ┌─────────────────┐      ┌─────────────────────────────┐   │
│  │  React Frontend │ ───► │  FastAPI Backend            │   │
│  │  (Static Build) │      │  - Intent parsing           │   │
│  │                 │      │  - Python generation scripts│   │
│  │  /chat UI       │      │  - Serves generated files   │   │
│  └─────────────────┘      └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  Google Gemini API  │
                         └─────────────────────┘
```

## Prerequisites

1. **GitHub Account** - Your code needs to be in a GitHub repository
2. **Railway Account** - Sign up at [railway.app](https://railway.app)
3. **Google API Key** - Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Step 1: Push Code to GitHub

If you haven't already, push this project to GitHub:

```bash
# Initialize git if needed
git init

# Add all files
git add .

# Commit
git commit -m "Initial deployment setup"

# Add your GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push
git push -u origin main
```

## Step 2: Deploy to Railway

### Option A: Railway Dashboard (Recommended)

1. Go to [railway.app](https://railway.app) and sign in
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Choose your repository
5. Railway will automatically detect the Dockerfile

### Option B: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

## Step 3: Configure Environment Variables

In the Railway dashboard:

1. Go to your project → **Variables**
2. Add the following variable:

| Variable | Value |
|----------|-------|
| `GOOGLE_API_KEY` | Your Google Gemini API key |

## Step 4: Get Your Domain

1. In Railway dashboard, go to **Settings** → **Networking**
2. Click **"Generate Domain"** to get a `.railway.app` subdomain
3. Or add a custom domain if you have one

## Step 5: Test Your Deployment

Visit your Railway URL (e.g., `https://your-app.railway.app`)

Try these example prompts:
- "Give me a potion icon"
- "Create a primary CTA that says CONFIRM"
- "Make a fire damage decreased boon"
- "Generate a card for frost queen 3 star calling cunning"

---

## Local Development

### Backend Only

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r backend/requirements.txt

# Run backend
cd backend
uvicorn main:app --reload --port 8000
```

### Frontend Only

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server proxies API requests to `localhost:8000`.

### Full Stack with Docker

```bash
# Build and run
docker-compose up --build

# Access at http://localhost:8000
```

---

## Auto-Deploy on Git Push

Railway automatically deploys when you push to your connected branch:

```bash
# Make changes
git add .
git commit -m "Update feature"
git push origin main

# Railway deploys automatically!
```

---

## Supported Asset Types

| Type | Example Prompt |
|------|---------------|
| **Icon** | "Give me a potion icon", "sword icon", "shield icon" |
| **CTA Button** | "Create a primary CTA that says CONFIRM", "secondary button labeled CANCEL" |
| **Boon** | "fire damage increased boon", "ice resistance debuff" |
| **Card** | "frost queen 3 star cunning card", "shadow knight 5star might" |
| **Gacha** | "gacha with 2 primals", "pull screen 1 5star primal 9 sorcery" |

---

## Troubleshooting

### Build Fails

1. Check Railway build logs
2. Ensure all dependencies are in `backend/requirements.txt`
3. Verify Dockerfile syntax

### Generation Fails

1. Check that `GOOGLE_API_KEY` is set correctly
2. Verify API key has Gemini access
3. Check Railway runtime logs

### Assets Not Loading

1. Ensure `assets/` folder is committed to git
2. Check that fonts are included
3. Verify paths in scripts

---

## Cost Considerations

- **Railway**: Free tier includes $5/month credit, usually enough for light usage
- **Google Gemini API**: Check current pricing at [ai.google.dev/pricing](https://ai.google.dev/pricing)

---

## File Structure

```
ICONBTN/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── routers/
│   │   └── generate.py      # API endpoints
│   ├── services/
│   │   └── parser.py        # Intent parsing
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   │       └── Chat.jsx     # Main chat UI
│   ├── package.json
│   └── vite.config.js
├── scripts/                  # Generation scripts
├── assets/                   # Reference images
├── fonts/                    # Font files
├── Dockerfile               # Production build
├── railway.json             # Railway config
└── docker-compose.yml       # Local development
```
