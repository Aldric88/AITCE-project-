from pymongo import MongoClient
from app.config import settings

client = MongoClient(settings.MONGO_URI)
db = client[settings.DB_NAME]

users_collection = db["users"]
notes_collection = db["notes"]
uploads_collection = db["uploads"]
moderation_logs_collection = db["moderation_logs"]
likes_collection = db["likes"]
bookmarks_collection = db["bookmarks"]
leaderboard_collection = db["leaderboard_points"]
purchases_collection = db["purchases"]
reviews_collection = db["reviews"]
reports_collection = db["reports"]
disputes_collection = db["disputes"]
