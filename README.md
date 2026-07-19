# QR Lost Item Finder — Secure & Anonymous QR Tag Platform

An elegant, premium, responsive web application for managing secure QR code tags attached to your physical items (backpacks, wallets, keys, laptops). When someone scans a lost item's QR code, they can securely and anonymously contact the owner via voice calls or SMS without either party exposing their private phone numbers, thanks to Twilio Proxy routing.

---

## 🚀 How to Run the Project Locally

This application consists of a **FastAPI** backend, a **React (Vite)** frontend, and a **PostgreSQL** database.

### 1. Database Setup (PostgreSQL)
Ensure you have PostgreSQL running locally. Create a database called `lostitem`.
Verify your database connection parameters match the `.env` settings:
```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=lostitem
SECRET_KEY=changeme
JWT_ALGORITHM=HS256
ALLOW_LEGACY_AUTH=False
FRONTEND_URL=http://localhost:5173
```

### 2. Run the Backend Server (FastAPI)
1. Open a terminal at the **root** of the project (`d:\qrcode`).
2. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. Run the FastAPI application using Uvicorn (make sure you are in the root folder):
   ```bash
   uvicorn backend.main:app --reload
   ```
   The backend will start and run on `http://127.0.0.1:8000`.

### 3. Run the Frontend App (React)
1. Open a new terminal and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev
   ```
   The frontend will be available at `http://localhost:5173`. Any API calls to `/api` are automatically proxied to the backend at `http://127.0.0.1:8000`.

---

## 🧪 Running Tests

We have a comprehensive automated test suite in the backend covering rate limiting, Twilio relay, PDF rendering, validation, and free-tier subscription limits.

To run the tests:
```bash
# In the root or backend directory
pytest -v
```

---

## 🎨 Features & Frontend Upgrade

We have upgraded the frontend to feature a premium, glassmorphic User Workspace:
1. **Secure Registration & Login**: JWT bearer auth via `Authorization: Bearer <token>` from backend login/signup.
2. **Interactive Workspace Dashboard**: 
   - View list of items, creation stats, and active limit indicators.
   - Live status toggles (`Active` $\leftrightarrow$ `Paused` $\leftrightarrow$ `Lost`).
   - Single tag QR previewer modals.
3. **Print Export Features**:
   - Single-item PDF card downloads.
   - Bulk item select to print sheets (supports 6 or 12 layouts per sheet) generated asynchronously in backend workers.

---

## ☁️ Production Deployment

The project is structured to easily deploy to **Render** (Backend) and **Vercel** (Frontend).

### 1. Deploying Backend to Render
You can deploy using Render's Blueprint feature or manual settings:

#### Option A: Blueprint Deploy (Recommended)
1. Go to your Render Dashboard and choose **Blueprints** -> **New Blueprint Instance**.
2. Connect your Git repository.
3. Render will automatically parse the `render.yaml` file in the root, spin up the PostgreSQL database (`qrcode-db`), build the Docker image, auto-generate a secure `SECRET_KEY`, and prompt you to input the remaining config variables (`APP_DOMAIN`, `FRONTEND_URL`, etc.).

#### Option B: Manual Setup
1. Create a new **Web Service** on [Render](https://render.com/). Connect your Git repository.
2. Choose the **Docker** runtime.
3. Add the required **Environment Variables** (see below).

#### Required Backend Environment Variables on Render:
- `DATABASE_URL`: Full connection string (e.g. `postgresql+asyncpg://...`)
- `DATABASE_SSL`: `True` (enables secure connection)
- `APP_ENV`: `production`
- `SECRET_KEY`: A secure long random string
- `APP_DOMAIN`: Your backend deployment URL (e.g. `https://backend.onrender.com`)
- `FRONTEND_URL`: Your Vercel frontend URL (e.g. `https://frontend.vercel.app`)
- `QR_BASE_URL`: Your Vercel frontend URL (e.g. `https://frontend.vercel.app`)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PROXY_SERVICE_SID`, `TWILIO_PHONE_NUMBER` (if using Twilio Proxy relays)
- `EMAIL_FROM`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` (for Gmail/SMTP password recovery)

---

### 2. Deploying Frontend to Vercel
1. Create a new project on [Vercel](https://vercel.com/).
2. Select your repository and set the **Framework Preset** to **Vite**.
3. Set the **Root Directory** to `frontend`.
4. Configure the following **Environment Variable**:
   - `VITE_API_URL`: Your backend URL on Render (e.g. `https://backend.onrender.com`)
5. Click **Deploy**. Vercel will build the frontend using `npm run build` and route client URLs correctly via `vercel.json`.

