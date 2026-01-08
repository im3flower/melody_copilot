<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />
</div>

# Melody Copilot UI

Custom React/Vite front-end for the Melody Copilot backend. It talks to the FastAPI `/complete` endpoint and paints a grey/orange piano-roll workspace.

## Quick start

1. **Install dependencies**
   ```
   npm install
   ```
2. **Configure the backend URL**
   - Edit `.env.local` and set `VITE_API_URL` (defaults to `http://localhost:8000`).
   - Make sure the FastAPI server from the repo root is running (`uvicorn main:app --port 8000 --app-dir bin`).
3. **Run the dev server**
   ```
   npm run dev
   ```
   The app will be available on `http://localhost:5173`.

4. **Build for production**
   ```
   npm run build
   ```

## Features

- Auto-loads `default.mid` from the backend to pre-fill the note textarea and BPM.
- Grey/orange compact layout suitable for embedding.
- Calls the backend `/complete` endpoint and surfaces the added notes plus request payload.
