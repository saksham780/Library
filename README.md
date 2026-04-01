# 📚 Library Management System — Library Management System

A full-stack library management system built with **Flask + SQLAlchemy** and a professional dark-academic UI.

## Features
- **Books** — Add, edit, delete, search, filter by genre/availability
- **Members** — Register, manage, view borrow history
- **Transactions** — Issue books, process returns, fine calculation
- **Dashboard** — Live stats, 7-day activity chart, genre breakdown
- **Search** — Global search across books and members
- **Persistent DB** — SQLite locally; PostgreSQL on cloud platforms

---

## 🚀 Local Development

```bash
# 1. Clone / unzip the project
cd library-management

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Open http://localhost:5000 — demo data is seeded automatically on first run.

---

## ☁️ Deploy to Render (Free)

1. Push this folder to a **GitHub repo**
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Runtime**: Python 3
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT`
5. Add environment variable: `SECRET_KEY` = (any random string)
6. Click **Deploy**

### Using PostgreSQL on Render
- Add a **PostgreSQL** database in Render
- Copy the **Internal Database URL**
- Add env var: `DATABASE_URL` = (paste the URL)
- Render automatically handles `postgres://` → `postgresql://` via our code

---

## ☁️ Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway init
railway up
```

Add `DATABASE_URL` env var pointing to a Railway PostgreSQL plugin.

---

## ☁️ Deploy to Heroku

```bash
heroku create your-library-app
heroku addons:create heroku-postgresql:mini
git push heroku main
```

---

## 🗄️ Project Structure

```
library-management/
├── app.py              # Flask app + all REST API routes
├── models.py           # SQLAlchemy models (Book, Member, Transaction)
├── requirements.txt    # Python dependencies
├── Procfile            # Gunicorn start command
├── templates/
│   └── index.html      # Jinja2 SPA template
└── static/
    ├── css/style.css   # Dark-academic CSS design system
    └── js/app.js       # Frontend JS — API calls, CRUD, UI
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Stats + chart data |
| GET/POST | `/api/books` | List / add books |
| GET/PUT/DELETE | `/api/books/<id>` | Get / update / delete book |
| GET/POST | `/api/members` | List / add members |
| GET/PUT/DELETE | `/api/members/<id>` | Get / update / delete member |
| POST | `/api/transactions/borrow` | Issue a book |
| POST | `/api/transactions/<id>/return` | Return a book |
| GET | `/api/transactions` | List transactions with filters |
| GET | `/api/search?q=` | Global search |


Features added: Clickable dashboard and Gemini chatbot for book details and suggestions.