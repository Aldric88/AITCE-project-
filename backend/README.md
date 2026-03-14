# Notes Platform API – Phase 1 (Auth + Users + RBAC)

## Setup

1. **MongoDB** – Run MongoDB locally (`mongod`) or set `MONGO_URI` in `.env` for Atlas.

2. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. **Apply DB indexes (migration step)**
   ```bash
   python migrations/apply_indexes.py
   ```

3. **Environment** – Copy `.env.example` to `.env` and set `JWT_SECRET_KEY` for production.

## Run

```bash
uvicorn app.main:app --reload --port 8001
```

Start AI worker in a second terminal:
```bash
python run_ai_worker.py
```

- API: http://127.0.0.1:8001  
- Swagger: http://127.0.0.1:8001/docs  

## Endpoints

| Method | Endpoint            | Auth    | Description                    |
|--------|---------------------|---------|--------------------------------|
| POST   | `/auth/signup`      | No      | Student signup                 |
| POST   | `/auth/login`       | No      | Login, returns JWT             |
| GET    | `/auth/me`          | Bearer  | Current user profile           |
| GET    | `/auth/moderator-area` | Moderator/Admin | Example RBAC route |

## Auth

- **Login** returns `{ "access_token": "...", "token_type": "bearer" }`.
- Use: `Authorization: Bearer <token>` for protected routes.

## Roles

- `student` – default on signup  
- `moderator` – set in DB for now  
- `admin` – set in DB for now  

## Security + Runtime Notes

- `JWT_SECRET_KEY` is required. The app will fail fast if it is missing.
- Authentication now uses `HttpOnly` auth cookies by default.
- Rate limits use Redis sliding window when `REDIS_URL` is reachable, with in-memory fallback for local development.
- Paid notes now require Razorpay checkout (`/payments/create-order` + `/payments/verify`).
- Configure `RAZORPAY_WEBHOOK_SECRET` and point Razorpay webhook to `POST /payments/webhook`.
- Access + refresh tokens are cookie-based with refresh rotation (`/auth/refresh`) and token revocation on logout.

## AI Moderation Modes

- `POST /ai/analyze-note/{note_id}` now uses a hybrid analyzer:
  - Reuses previous analysis by `file_hash` (no repeated model cost).
  - Tries Gemini first (`MODERATION_AI_MODE=auto` with `GEMINI_API_KEY`), then Ollama.
  - Falls back to deterministic rules engine if model calls are unavailable.
- Supported values:
  - `MODERATION_AI_MODE=gemini|ollama|auto|rules`
  - `GEMINI_API_KEY=<your_key>`
  - `GEMINI_MODEL=gemini-2.5-flash`
- Regenerate bypassing cache:
  - `POST /ai/reports/{note_id}/regenerate`
- Moderator-focused queue:
  - `GET /ai/moderation-queue` (returns only `needs_moderator_review` items)

## AI Cluster Classification (Signup Domain Fallback)

- Signup still prefers deterministic `college_domains` mapping.
- For unknown domains, optional Gemini/Ollama inference can suggest/assign cluster type.
- Environment variables:
  - `CLUSTER_AI_MODE=auto|gemini|ollama|off` (default: `auto`)
  - `CLUSTER_AI_GEMINI_MODEL` (default: `gemini-2.5-flash`)
  - `CLUSTER_AI_OLLAMA_URL` (default: `http://127.0.0.1:11434/api/generate`)
  - `CLUSTER_AI_OLLAMA_MODEL` (default: `llama3.1:8b`)
  - `CLUSTER_AI_TIMEOUT_SECONDS` (default: `2.5`)
  - `CLUSTER_AI_AUTO_ASSIGN_MIN_CONFIDENCE` (default: `0.8`)
