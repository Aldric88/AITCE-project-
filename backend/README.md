# Notes Platform API – Phase 1 (Auth + Users + RBAC)

## Setup

1. **MongoDB** – Run MongoDB locally (`mongod`) or set `MONGO_URI` in `.env` for Atlas.

2. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Environment** – Copy `.env.example` to `.env` and set `JWT_SECRET_KEY` for production.

## Run

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000  
- Swagger: http://127.0.0.1:8000/docs  

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
