import os

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
from app.routes.purchase_routes import router as purchase_router
from app.routes.secure_view_routes import router as secure_router
from app.routes.seller_routes import router as seller_router
from app.routes.review_routes import router as review_router
from app.routes.report_routes import router as report_router
from app.routes.dispute_routes import router as dispute_router
from app.routes.seller_analytics_routes import router as seller_analytics_router

app = FastAPI(title="Notes Platform API")

# CORS for React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production put frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads folder exists
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# ✅ REMOVED public file serving - now using secure token-gated access
# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(notes_router)
app.include_router(file_router)
app.include_router(like_router)
app.include_router(bookmark_router)
app.include_router(leaderboard_router)
app.include_router(purchase_router)
app.include_router(secure_router)
app.include_router(seller_router)
app.include_router(review_router)
app.include_router(report_router)
app.include_router(dispute_router)
app.include_router(seller_analytics_router)


@app.get("/")
def root():
    return {"status": "Backend running ✅"}
