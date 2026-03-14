# Notes Market - Team Feature Documentation

## 1. System Overview

Notes Market is a full-stack notes sharing/selling platform with:
- JWT-based authentication
- Role-based moderation/admin controls
- File upload + secure preview/download controls
- Paid/free unlock flows
- Social graph (follow/feed), comments, likes, bookmarks
- Seller analytics, creator suggestions, notifications
- AI-assisted moderation with Gemini

Primary entry points:
- Frontend app shell: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/App.jsx`
- Backend app composition: `/Users/aldricanto/Documents/Notes market/backend/app/main.py`


## 2. Technology and Runtime

### Frontend
- React + Vite + React Router + Axios + Tailwind
- Global styling and design tokens: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/index.css`
- Tailwind config: `/Users/aldricanto/Documents/Notes market/notes-frontend/tailwind.config.js`
- API client and auth header injection: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/api/axios.js`
- API base constant for static/iframe URLs: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/api/baseUrl.js`

### Backend
- FastAPI + MongoDB (PyMongo) + JWT + bcrypt
- DB collections declared in: `/Users/aldricanto/Documents/Notes market/backend/app/database.py`
- Auth dependencies and RBAC: `/Users/aldricanto/Documents/Notes market/backend/app/utils/dependencies.py`
- JWT/password helpers: `/Users/aldricanto/Documents/Notes market/backend/app/utils/security.py`

### Environment and Config
- Backend env template: `/Users/aldricanto/Documents/Notes market/backend/.env.example`
- Config loader: `/Users/aldricanto/Documents/Notes market/backend/app/config.py`
- Frontend backend URL uses `VITE_API_BASE_URL` fallback `http://127.0.0.1:8001`


## 3. Application Architecture

### 3.1 Frontend Architecture
- `AuthProvider` bootstraps user with `/auth/me` on app load and handles token invalidation.
  - `/Users/aldricanto/Documents/Notes market/notes-frontend/src/auth/AuthContext.jsx`
- Route-level protection uses token presence (`ProtectedRoute`).
  - `/Users/aldricanto/Documents/Notes market/notes-frontend/src/auth/ProtectedRoute.jsx`
- Shared `Layout` provides:
  - sticky brand/header
  - profile dropdown
  - role-aware navigation
  - grouped nav menus + mobile menu
  - `/Users/aldricanto/Documents/Notes market/notes-frontend/src/components/Layout.jsx`

### 3.2 Backend Architecture
- `main.py` wires all routers and middleware.
- CORS is allow-list driven from `CORS_ORIGINS`.
- Static serving is intentionally restricted to `/uploads/profile` only.
- Private note files are resolved by backend routes and are not publicly mounted.
- AI debug routes are only mounted when `ENABLE_AI_DEBUG=true`.


## 4. Data Model and Collections

Collections used (from `database.py`):
- Core: `users`, `notes`, `uploads`, `purchases`, `reviews`, `reports`, `disputes`
- Moderation/quality: `moderation_logs`, `ai_reports`
- Discovery/social: `likes`, `bookmarks`, `follows`, `notifications`, `note_comments`, `comment_likes`, `note_requests`, `bundles`
- Access/session: `view_sessions`
- Ranking/trust: `leaderboard_points`, `college_domains`, `clusters`, `colleges`

Helper mappers:
- User mapper: `/Users/aldricanto/Documents/Notes market/backend/app/models/user_model.py`
- Note mapper: `/Users/aldricanto/Documents/Notes market/backend/app/models/note_model.py`


## 5. Authentication, Authorization, and Identity

### 5.1 Auth Endpoints
File: `/Users/aldricanto/Documents/Notes market/backend/app/routes/auth_routes.py`
- `POST /auth/signup`
  - Validates uniqueness
  - Assigns `cluster_id` via email domain mapping (`college_domains`)
  - Sets verification flags (`verified_by_domain`, `requires_manual_selection`)
- `POST /auth/login`
  - OAuth form payload (`username=email`, `password`)
  - Rate limited by `login_limiter`
  - Returns JWT
- `GET /auth/me`
  - Returns user profile + follower/following counts

### 5.2 RBAC
- Role checks via `require_role([...])` dependency.
- Admin-only examples: user management, dispute queue actions.
- Moderator/admin: moderation actions and report queue.

### 5.3 Login/Signup Fixes Implemented
- Frontend API base was normalized to `127.0.0.1:8001` fallback to avoid localhost/port mismatch.
  - `/Users/aldricanto/Documents/Notes market/notes-frontend/src/api/axios.js`
- Signup response model mismatch around `cluster_id` fixed to `Optional[str]`.
  - `/Users/aldricanto/Documents/Notes market/backend/app/schemas/user_schema.py`


## 6. Notes Lifecycle and Content Pipeline

### 6.1 Upload + Note Creation
- File upload endpoint: `POST /files/upload`
  - Streams file to `uploads/private`
  - Checks extension and max size (15MB)
  - Computes SHA256 and deduplicates
  - Stores metadata in `uploads`
  - `/Users/aldricanto/Documents/Notes market/backend/app/routes/file_routes.py`
- Note creation endpoint: `POST /notes/`
  - Validates note type requirements
  - Validates paid-note constraints + seller verification
  - Ensures `file_url` belongs to uploader and is not reused
  - Sets `status=pending`
  - Optionally triggers AI auto-analysis logic
  - `/Users/aldricanto/Documents/Notes market/backend/app/routes/note_routes.py`

### 6.2 Moderation
- Queue and actions:
  - `GET /notes/pending`
  - `PATCH /notes/{id}/approve`
  - `PATCH /notes/{id}/reject`
  - Override endpoints for approved/rejected transitions
- Moderation UI(s):
  - `/Users/aldricanto/Documents/Notes market/notes-frontend/src/pages/ModerationDashboard.jsx`
  - `/Users/aldricanto/Documents/Notes market/notes-frontend/src/pages/ModerationPanel.jsx`

### 6.3 Discovery and Listing
- Primary feed: `GET /notes`
  - Filters: dept, semester, subject, exam_tag, search
  - Sorting options
  - Pagination via skip/limit
  - Trust enrichment via aggregation joins (uploader/reviews/seller sales)
  - Access enrichment (`has_access`)
- Trending: `GET /notes/trending`
- Details: `GET /notes/{id}/details`

### 6.4 Dashboard UX
File: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/pages/Dashboard.jsx`
- Infinite scroll pagination
- Multi-filter search panel
- Like/bookmark/purchase/download actions
- Suggestion rail for creators
- Optimistic UI updates for like/bookmark states


## 7. Purchase, Access Control, Viewer, and Download

### 7.1 Purchase Model
File: `/Users/aldricanto/Documents/Notes market/backend/app/routes/purchase_routes.py`
- Canonical route prefix: `/purchase`
- `POST /purchase/{note_id}` unlocks free/paid notes (currently direct success flow)
- `GET /purchase/my` returns user purchase records
- `GET /purchase/has/{note_id}` returns access boolean

### 7.2 Backward Compatibility and Migration
- Purchase queries check both legacy and canonical fields:
  - `buyer_id` + `status=success`
  - or `user_id` + `status in [success, paid, free]`
- Migration script: `/Users/aldricanto/Documents/Notes market/backend/migrate_purchases_schema.py`
  - normalizes status and purchase type
  - fills canonical `buyer_id`

### 7.3 Secure Viewing
File: `/Users/aldricanto/Documents/Notes market/backend/app/routes/secure_view_routes.py`
- Session-based viewer flow:
  - `POST /secure/session/start/{note_id}` creates short-lived tokenized session
  - `GET /secure/session/file/{note_id}?token=...` serves watermarked stream
- Direct secure file endpoint:
  - `GET /secure/note/{note_id}/file`
- Download endpoint:
  - `GET /secure/note/{note_id}/download`
- Rate limiting via user-level limiter for secure endpoints.
- Watermarking utilities:
  - PDF: `/Users/aldricanto/Documents/Notes market/backend/app/utils/pdf_watermark.py`
  - Image: `/Users/aldricanto/Documents/Notes market/backend/app/utils/image_watermark.py`

### 7.4 Download Rules
File: `/Users/aldricanto/Documents/Notes market/backend/app/routes/download_routes.py`
- `GET /download/{note_id}`
- Owners can download.
- Non-owners must have unlock/purchase.
- Paid notes are "view-only" for non-owners by business rule.

### 7.5 Preview Rules
File: `/Users/aldricanto/Documents/Notes market/backend/app/routes/preview_routes.py`
- Free notes: full PDF preview
- Paid notes: limited-page cached preview with watermark
- Preview cache utility:
  - `/Users/aldricanto/Documents/Notes market/backend/app/utils/pdf_preview.py`


## 8. Reviews, Reports, Disputes

### 8.1 Reviews
File: `/Users/aldricanto/Documents/Notes market/backend/app/routes/review_routes.py`
- One review per user per note.
- Paid note reviews require purchase unless uploader.
- Endpoints:
  - `POST /reviews/note/{id}`
  - `GET /reviews/note/{id}`
  - `GET /reviews/note/{id}/summary`

### 8.2 Reports
File: `/Users/aldricanto/Documents/Notes market/backend/app/routes/report_routes.py`
- User report submission for note quality/abuse.
- Moderator/admin pending queue and resolve endpoint.

### 8.3 Disputes
File: `/Users/aldricanto/Documents/Notes market/backend/app/routes/dispute_routes.py`
- Buyer can dispute only after purchase/unlock.
- Admin can approve/reject pending disputes.

### 8.4 Frontend Modals
- Review modal: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/components/ReviewModal.jsx`
- Report modal: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/components/ReportModal.jsx`
- Dispute modal: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/components/DisputeModal.jsx`


## 9. Social Layer (Follow, Comments, Notifications)

### 9.1 Follow System
File: `/Users/aldricanto/Documents/Notes market/backend/app/routes/follow_routes.py`
- Follow/unfollow creator
- Fetch my following IDs
- Followers/following lists
- Feed from followed creators (`/follow/feed`)
- Follows trigger notifications via `notify()`

### 9.2 Comments/Q&A
File: `/Users/aldricanto/Documents/Notes market/backend/app/routes/comment_routes.py`
- Threaded comments with replies (`parent_id`)
- Like/unlike comments
- Pin/unpin comment (owner or staff)
- Pinned-first ordering on parent comments

### 9.3 Notifications
- Helper: `/Users/aldricanto/Documents/Notes market/backend/app/utils/notify.py`
- Routes: `/Users/aldricanto/Documents/Notes market/backend/app/routes/notification_routes.py`
  - list notifications
  - mark as read

### 9.4 Frontend Social Components
- Follow button: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/components/FollowButton.jsx`
- Comments panel: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/components/Comments.jsx`
- Notifications page: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/pages/Notifications.jsx`


## 10. Creator and Profile Experience

### 10.1 User/Creator Profile APIs
- Creator profile endpoint: `/users/{id}/profile`
  - `/Users/aldricanto/Documents/Notes market/backend/app/routes/user_routes.py`
- Own profile management:
  - upload picture: `/profile/upload-pic`
  - patch details: `/profile/me`
  - `/Users/aldricanto/Documents/Notes market/backend/app/routes/profile_routes.py`

### 10.2 Email Verification
- Send OTP / confirm OTP endpoints:
  - `/verify/send-otp`
  - `/verify/confirm-otp`
  - `/Users/aldricanto/Documents/Notes market/backend/app/routes/verify_routes.py`
- Mail utility:
  - `/Users/aldricanto/Documents/Notes market/backend/app/utils/email_service.py`


## 11. Discovery, Suggestions, Requests, Bundles

### 11.1 Suggestions
- Suggested creators by peer similarity and contribution:
  - `/suggestions/creators`
- Top creators in same department:
  - `/suggestions/top-creators`
- Backend: `/Users/aldricanto/Documents/Notes market/backend/app/routes/suggestion_routes.py`
- Frontend:
  - `/Users/aldricanto/Documents/Notes market/notes-frontend/src/components/SuggestedCreators.jsx`
  - `/Users/aldricanto/Documents/Notes market/notes-frontend/src/pages/TopCreators.jsx`

### 11.2 Requests
- Note demand posting and closure workflow.
- Backend: `/Users/aldricanto/Documents/Notes market/backend/app/routes/request_routes.py`
- Frontend: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/pages/Requests.jsx`

### 11.3 Bundles
- Seller can package >=2 approved own notes into bundle.
- Backend: `/Users/aldricanto/Documents/Notes market/backend/app/routes/bundle_routes.py`
- Frontend: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/pages/Bundles.jsx`


## 12. Seller, Leaderboard, Admin, and Payment

### 12.1 Seller Dashboard
- Metrics: total notes, sales, earnings, top notes
- Backend: `/Users/aldricanto/Documents/Notes market/backend/app/routes/seller_analytics_routes.py`
- Frontend: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/pages/SellerDashboard.jsx`

### 12.2 Leaderboard
- Point aggregation from likes/approvals
- Backend: `/Users/aldricanto/Documents/Notes market/backend/app/routes/leaderboard_routes.py`
- Frontend: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/pages/Leaderboard.jsx`

### 12.3 Admin Controls
- List/filter users
- Change role
- Ban/unban users
- Backend: `/Users/aldricanto/Documents/Notes market/backend/app/routes/admin_routes.py`

### 12.4 Payment Integration
- Razorpay order creation and signature verification endpoints
- Backend: `/Users/aldricanto/Documents/Notes market/backend/app/routes/payment_routes.py`


## 13. AI Moderation Features

### 13.1 AI Endpoints
Primary AI router: `/Users/aldricanto/Documents/Notes market/backend/app/routes/ai_routes.py`
- `POST /ai/analyze/{note_id}` strict metadata-vs-content validation
- report retrieval/summary/export/regenerate endpoints
- compatibility endpoint `/ai/analyze-note/{note_id}`

Additional variant router: `/Users/aldricanto/Documents/Notes market/backend/app/routes/gemini_ai_routes.py`
- lighter analysis + `/ai/report/{note_id}` format

Debug router (gated by env): `/Users/aldricanto/Documents/Notes market/backend/app/routes/ai_debug.py`

### 13.2 AI Data Stored
- Validation booleans, spam score, topic extraction, warning list
- Moderation metadata + operator identity
- Report status flags and summary metrics


## 14. UI/Styling System and Navigation Redesign

### 14.1 Design Direction
- Neutral monochrome base (black/white/grays)
- Sharp borders, block typography, minimal shadows
- Utility component classes (`btn-primary`, `btn-secondary`, `input-surface`, etc.)

### 14.2 Navigation Improvements Implemented
File: `/Users/aldricanto/Documents/Notes market/notes-frontend/src/components/Layout.jsx`
- Primary links always visible:
  - Dashboard, Trending, Upload, Purchases, Alerts
- Grouped secondary menus:
  - Library, Sell, Community
- Mobile menu with grouped sections
- Role-based Moderation link retained
- Active states improved for readability and hierarchy


## 15. Security Controls Implemented

- JWT auth + role enforcement.
- Login rate limiting (IP-based).
- Search/feed rate limiter on notes endpoint.
- User-based rate limiter on secure view/download path.
- Private file storage not publicly mounted.
- Secure file resolution via upload metadata + path normalization checks.
- Watermarked secure viewer streams for PDF/images.
- Purchase checks include canonical + legacy schema variants.


## 16. Testing and Verification Assets

- Manual full-flow script:
  - `/Users/aldricanto/Documents/Notes market/backend/tests/test_full_flow.py`
- Manual security test script:
  - `/Users/aldricanto/Documents/Notes market/backend/tests/test_security_manual.py`
- Schema migration utility:
  - `/Users/aldricanto/Documents/Notes market/backend/migrate_purchases_schema.py`


## 17. Known Integration Gaps / Technical Debt

These are important for teammates before adding features:

1. Route/module size is still high for a few core screens/routes.
- Backend `/Users/aldricanto/Documents/Notes market/backend/app/routes/note_routes.py` remains a large mixed-responsibility module.
- Frontend `/Users/aldricanto/Documents/Notes market/notes-frontend/src/pages/ModerationDashboard.jsx` remains a large single-page component.

2. Frontend test depth is still limited.
- CI validates lint/build, but integration-level React user-flow tests are still thin.

3. SSE notification stream is optimized for low query load, but cross-process push semantics depend on deployment topology.
- For horizontally scaled workers, prefer Redis-backed pub/sub fan-out for strict real-time parity.

4. Offline mode currently focuses on shell + cached library metadata.
- Full binary note sync and conflict-aware annotation synchronization are still incremental roadmap items.

5. Typed client adoption is in progress.
- New typed wrappers should be used consistently page-by-page to fully remove route drift risk.


## 18. Recommended Team Conventions Going Forward

- Standardize API naming to singular/plural per domain and enforce in a shared API contract doc.
- Keep frontend API paths in one typed client layer to avoid route drift.
- Add a backend contract test for each frontend page data shape.
- Add smoke tests for critical flows:
  - signup/login/me
  - upload->create note
  - purchase->secure view
  - comments/follow notifications
- Introduce lint rule or CI check for unresolved imports in route modules.


## 19. Quick Start for New Teammates

1. Backend
- Copy `.env.example` to `.env`
- Set MongoDB URI and JWT secret
- Run `uvicorn app.main:app --reload` from `/Users/aldricanto/Documents/Notes market/backend`

2. Frontend
- Set `VITE_API_BASE_URL` if needed
- Run `npm run dev` from `/Users/aldricanto/Documents/Notes market/notes-frontend`

3. Verify core flows
- Signup -> Login -> Dashboard -> Upload -> Moderate -> Purchase -> Secure View
