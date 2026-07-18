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
```

### 2. Run the Backend Server (FastAPI)
1. Open a terminal and navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI application using Uvicorn:
   ```bash
   uvicorn main:app --reload
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
1. **Secure Registration & Login**: Authentic credentials stored in localStorage mapped to backend Stub Authorization.
2. **Interactive Workspace Dashboard**: 
   - View list of items, creation stats, and active limit indicators.
   - Live status toggles (`Active` $\leftrightarrow$ `Paused` $\leftrightarrow$ `Lost`).
   - Single tag QR previewer modals.
3. **Print Export Features**:
   - Single-item PDF card downloads.
   - Bulk item select to print sheets (supports 6 or 12 layouts per sheet) generated asynchronously in backend workers.
