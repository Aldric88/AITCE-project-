import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes.auth_routes import router as auth_router
from app.routes.admin_routes import router as admin_router
from app.routes.note_routes import router as notes_router
from app.routes.file_routes import router as file_router
from app.routes.like_routes import router as like_router
from app.routes.bookmark_routes import router as bookmark_router
from app.routes.leaderboard_routes import router as leaderboard_router
from app.routes.purchase_routes import (
    router as purchase_router,
    router_plural as purchases_router,
    router_library as library_router,
)
from app.routes.secure_view_routes import router as secure_router
from app.routes.seller_routes import router as seller_router
from app.routes.payment_routes import router as payment_router
from app.routes.review_routes import router as review_router
from app.routes.report_routes import router as report_router
from app.routes.dispute_routes import router as dispute_router
from app.routes.seller_analytics_routes import router as seller_analytics_router
from app.routes.ai_routes import router as ai_router
from app.routes.ai_debug import router as ai_debug_router
from app.routes.recommendation_routes import router as rec_router
from app.routes.request_routes import router as request_router
from app.routes.bundle_routes import router as bundle_router
from app.routes.verify_routes import router as verify_router
from app.routes.follow_routes import router as follow_router
from app.routes.profile_routes import router as profile_router
from app.routes.user_routes import router as user_router
from app.routes.suggestion_routes import router as suggestion_router
from app.routes.notification_routes import router as notification_router
from app.routes.preview_routes import router as preview_router
from app.routes.comment_routes import router as comment_router
from app.routes.download_routes import router as download_router
from app.routes.moderation_features_routes import router as moderation_features_router
from app.routes.ops_routes import router as ops_router
from app.routes.risk_routes import router as risk_router
from app.routes.space_routes import router as space_router
from app.routes.monetization_routes import router as monetization_router
from app.routes.note_features_routes import router as note_features_router
from app.routes.wallet_routes import router as wallet_router
from app.utils.observability import JsonLogFormatter, RequestIDMiddleware, SecurityHeadersMiddleware
from app.config import settings

app = FastAPI(title="Notes Platform API")
root_logger = logging.getLogger()
root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
if settings.LOG_JSON and root_logger.handlers:
    for h in root_logger.handlers:
        h.setFormatter(JsonLogFormatter())
elif not root_logger.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

# CORS for React
allowed_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://notes-market.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Idempotency-Key", "X-Request-ID"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Ensure upload folders exist
os.makedirs("uploads/private", exist_ok=True)
os.makedirs("uploads/profile", exist_ok=True)

# Serve only public profile images via static files
app.mount("/uploads/profile", StaticFiles(directory="uploads/profile"), name="profile_uploads")

# Routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(notes_router)
# note_moderation_router removed — AI auto-moderation replaces human moderation
app.include_router(note_features_router)
app.include_router(file_router)
app.include_router(like_router)
app.include_router(bookmark_router)
app.include_router(leaderboard_router)
app.include_router(purchase_router)
app.include_router(purchases_router)
app.include_router(library_router)
app.include_router(payment_router)
app.include_router(secure_router)
app.include_router(seller_router)
app.include_router(review_router)
app.include_router(report_router)
app.include_router(dispute_router)
app.include_router(seller_analytics_router)
app.include_router(ai_router)
# Only enable debug AI routes explicitly
if os.getenv("ENABLE_AI_DEBUG", "false").lower() == "true":
    app.include_router(ai_debug_router)
app.include_router(rec_router)
app.include_router(request_router)
app.include_router(bundle_router)
app.include_router(verify_router)
app.include_router(follow_router)
app.include_router(profile_router)
app.include_router(user_router)
app.include_router(suggestion_router)
app.include_router(notification_router)
app.include_router(preview_router)
app.include_router(comment_router)
app.include_router(download_router)
app.include_router(moderation_features_router)
app.include_router(ops_router)
app.include_router(risk_router)
app.include_router(space_router)
app.include_router(monetization_router)
app.include_router(wallet_router)


@app.get("/")
def root():
    return {"status": "Backend running ✅"}
