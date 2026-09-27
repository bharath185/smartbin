# SmartBin — Smart Waste Management System

An intelligent IoT-enabled waste monitoring and city collection management platform. SmartBin connects smart dustbins equipped with IoT sensors (ultrasonic fill-level monitoring, OLED status screens) to a centralized real-time dashboard for municipalities, drivers, and citizens.

---

## 🌟 Key Features

- **Real-Time Bin Monitoring**: Track fill levels, battery status, and location coordinates on interactive maps.
- **Role-Based Portals**:
  - **Municipality / Admin**: Fleet overview, route assignment, complaint triage, analytics, and driver management.
  - **Drivers**: Dedicated task queues, collection routes, QR code bin pickup verification, and completion reporting.
  - **Citizens / Customers**: Real-time bin map, complaint logging with photo uploads, and community leaderboard.
- **Live Updates**: WebSocket connection for live telemetry updates and event alerts.
- **RESTful API**: Fast and modular FastAPI backend with JWT authentication and SQLite/PostgreSQL support.
- **Firmware Support**: ESP32 sketches for fill-level sensing and OLED status reporting.

---

## 🏗️ Architecture

```
smartbin/
├── frontend/             # Responsive client web app (HTML5, modern CSS, vanilla JS)
│   ├── assets/           # CSS stylesheets, JS scripts, icons
│   ├── index.html        # Municipality management dashboard
│   ├── customer.html     # Citizen portal
│   ├── driver.html       # Driver field dashboard
│   ├── bin-map.html      # Geographic bin locator
│   └── ...               # Analytics, complaints, leaderboard, login, etc.
├── backend/              # FastAPI Python backend
│   ├── app/              # API routes, models, database schemas, and services
│   ├── requirements.txt  # Python dependencies
│   └── seed.py           # Sample data seeder
├── firmware/             # IoT Hardware firmware
│   └── esp32/            # ESP32 sketches and sensor drivers
├── vercel.json           # Vercel deployment configuration
├── start_backend.bat     # Windows one-click backend runner
└── start_frontend.bat    # Windows one-click frontend runner
```

---

## 🚀 Quick Start (Local Development)

### 1. Backend Setup

```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Backend API will be running at `http://localhost:8000` (API docs at `http://localhost:8000/docs`).

### 2. Frontend Setup

You can serve the static frontend using any local HTTP server:
```bash
cd frontend
python -m http.server 3000
```
Visit `http://localhost:3000` in your web browser.

Alternatively on Windows, use the helper scripts:
- Double-click `start_backend.bat`
- Double-click `start_frontend.bat`

---

## ☁️ Deployment

### Deploying Frontend to Vercel

SmartBin includes a root `vercel.json` for seamless deployment to Vercel:

1. Import this repository into [Vercel](https://vercel.com/new).
2. Leave the Root Directory as default (`.`) or set to `frontend`.
3. Click **Deploy**. Vercel will automatically route traffic and serve the dashboard.

---

## 🔒 Security & Environment Variables

Copy `.env.example` to `.env` in the `backend/` directory:
```bash
cp .env.example backend/.env
```
Ensure you set a secure `JWT_SECRET` and appropriate database connection string before deploying to production.
