from pymongo import MongoClient
from pymongo.errors import PyMongoError
import logging
from app.config import settings

logger = logging.getLogger(__name__)

client = MongoClient(
    settings.MONGO_URI,
    serverSelectionTimeoutMS=settings.MONGO_SERVER_SELECTION_TIMEOUT_MS,
)
db = client[settings.DB_NAME]

# Collections
users_collection = db["users"]
notes_collection = db["notes"]
uploads_collection = db["uploads"]
moderation_logs_collection = db["moderation_logs"]
likes_collection = db["likes"]
bookmarks_collection = db["bookmarks"]
leaderboard_collection = db["leaderboard_points"]
purchases_collection = db["purchases"]
ledger_entries_collection = db["ledger_entries"]
payment_events_collection = db["payment_events"]
payment_webhook_events_collection = db["payment_webhook_events"]
idempotency_keys_collection = db["idempotency_keys"]
refresh_tokens_collection = db["refresh_tokens"]
revoked_tokens_collection = db["revoked_tokens"]
ai_jobs_collection = db["ai_jobs"]
reviews_collection = db["reviews"]
reports_collection = db["reports"]
disputes_collection = db["disputes"]
requests_collection = db["note_requests"]
bundles_collection = db["bundles"]
follows_collection = db["follows"]
notifications_collection = db["notifications"]
comments_collection = db["note_comments"]
comment_likes_collection = db["comment_likes"]
view_sessions_collection = db["view_sessions"]
ai_reports_collection = db["ai_reports"]
moderation_rules_collection = db["moderation_rules"]
moderation_appeals_collection = db["moderation_appeals"]
audit_events_collection = db["audit_events"]
revalidation_jobs_collection = db["revalidation_jobs"]
college_domains_collection = db["college_domains"]
clusters_collection = db["clusters"]
colleges_collection = db["colleges"]
class_spaces_collection = db["class_spaces"]
space_memberships_collection = db["space_memberships"]
space_announcements_collection = db["space_announcements"]
space_notes_collection = db["space_notes"]
coupons_collection = db["coupons"]
campaigns_collection = db["campaigns"]
cluster_inference_candidates_collection = db["cluster_inference_candidates"]
request_pledges_collection = db["request_pledges"]
creator_passes_collection = db["creator_passes"]
pass_subscriptions_collection = db["pass_subscriptions"]
note_annotations_collection = db["note_annotations"]
note_versions_collection = db["note_versions"]
seller_experiments_collection = db["seller_experiments"]


def ensure_indexes():
    try:
        users_collection.create_index("email", unique=True, name="uniq_email")
    except PyMongoError as exc:
        logger.warning("Unable to create users.email unique index: %s", exc)

    try:
        notes_collection.create_index(
            [("status", 1), ("cluster_id", 1), ("dept", 1), ("semester", 1), ("created_at", -1)],
            name="notes_feed_filters",
        )
        notes_collection.create_index(
            [("status", 1), ("downloads", -1)],
            name="notes_status_downloads",
        )
        notes_collection.create_index(
            [("status", 1), ("avg_rating", -1)],
            name="notes_status_rating",
        )
        notes_collection.create_index(
            [("status", 1), ("price", 1)],
            name="notes_status_price",
        )
        notes_collection.create_index(
            [("uploader_id", 1), ("status", 1), ("created_at", -1)],
            name="notes_uploader_status_created",
        )
    except PyMongoError as exc:
        logger.warning("Unable to create notes indexes: %s", exc)

    try:
        uploads_collection.create_index("file_hash", unique=True, name="uniq_upload_file_hash")
        uploads_collection.create_index("file_url", unique=True, name="uniq_upload_file_url")
    except PyMongoError as exc:
        logger.warning("Unable to create uploads indexes: %s", exc)

    try:
        purchases_collection.create_index(
            [("note_id", 1), ("buyer_id", 1), ("status", 1)],
            name="purchases_note_buyer_status",
        )
        purchases_collection.create_index(
            [("note_id", 1), ("user_id", 1), ("status", 1)],
            name="purchases_note_user_status",
        )
        purchases_collection.create_index(
            [("razorpay_order_id", 1)],
            name="purchases_razorpay_order_id",
            unique=True,
            sparse=True,
        )
        purchases_collection.create_index(
            [("razorpay_payment_id", 1)],
            name="purchases_razorpay_payment_id",
            sparse=True,
        )
    except PyMongoError as exc:
        logger.warning("Unable to create purchases indexes: %s", exc)

    try:
        ledger_entries_collection.create_index(
            [("purchase_id", 1), ("entry_type", 1)],
            name="ledger_purchase_entry_type",
        )
        ledger_entries_collection.create_index(
            [("created_at", -1)],
            name="ledger_created_at",
        )
    except PyMongoError as exc:
        logger.warning("Unable to create ledger indexes: %s", exc)

    try:
        payment_webhook_events_collection.create_index(
            [("event_id", 1)],
            name="uniq_payment_webhook_event_id",
            unique=True,
        )
    except PyMongoError as exc:
        logger.warning("Unable to create payment webhook indexes: %s", exc)

    try:
        idempotency_keys_collection.create_index(
            [("key", 1), ("route", 1), ("user_id", 1)],
            name="uniq_idempotency_scope",
            unique=True,
        )
        idempotency_keys_collection.create_index(
            [("created_at", 1)],
            name="idempotency_created_at",
        )
        idempotency_keys_collection.create_index(
            [("created_at", 1)],
            name="idempotency_ttl_7d",
            expireAfterSeconds=7 * 24 * 3600,
        )
    except PyMongoError as exc:
        logger.warning("Unable to create idempotency indexes: %s", exc)

    try:
        refresh_tokens_collection.create_index(
            [("jti", 1)],
            name="uniq_refresh_jti",
            unique=True,
        )
        refresh_tokens_collection.create_index(
            [("user_id", 1), ("revoked", 1)],
            name="refresh_user_revoked",
        )
        refresh_tokens_collection.create_index(
            [("expires_at", 1)],
            name="refresh_expires_ttl",
            expireAfterSeconds=0,
        )
    except PyMongoError as exc:
        logger.warning("Unable to create refresh token indexes: %s", exc)

    try:
        revoked_tokens_collection.create_index(
            [("jti", 1)],
            name="uniq_revoked_jti",
            unique=True,
        )
        revoked_tokens_collection.create_index(
            [("expires_at", 1)],
            name="revoked_expires_ttl",
            expireAfterSeconds=0,
        )
    except PyMongoError as exc:
        logger.warning("Unable to create revoked token indexes: %s", exc)

    try:
        notes_collection.create_index(
            [("title", "text"), ("subject", "text"), ("tags", "text")],
            name="notes_text_search",
            default_language="english",
        )
    except PyMongoError as exc:
        logger.warning("Unable to create notes text index: %s", exc)

    try:
        ai_jobs_collection.create_index([("status", 1), ("created_at", 1)], name="ai_jobs_status_created")
    except PyMongoError as exc:
        logger.warning("Unable to create ai jobs indexes: %s", exc)

    try:
        moderation_rules_collection.create_index([("config_name", 1)], unique=True, name="uniq_moderation_config_name")
    except PyMongoError as exc:
        logger.warning("Unable to create moderation rules indexes: %s", exc)

    try:
        moderation_appeals_collection.create_index([("note_id", 1), ("status", 1)], name="appeals_note_status")
        moderation_appeals_collection.create_index([("created_at", -1)], name="appeals_created_at")
    except PyMongoError as exc:
        logger.warning("Unable to create appeals indexes: %s", exc)

    try:
        audit_events_collection.create_index([("note_id", 1), ("created_at", -1)], name="audit_note_created")
    except PyMongoError as exc:
        logger.warning("Unable to create audit indexes: %s", exc)

    try:
        revalidation_jobs_collection.create_index([("status", 1), ("created_at", 1)], name="revalidation_status_created")
    except PyMongoError as exc:
        logger.warning("Unable to create revalidation indexes: %s", exc)

    try:
        follows_collection.create_index(
            [("follower_id", 1), ("following_id", 1)],
            name="uniq_follow_edge",
            unique=True,
        )
        follows_collection.create_index([("following_id", 1)], name="follows_following_id")
    except PyMongoError as exc:
        logger.warning("Unable to create follows indexes: %s", exc)

    try:
        notifications_collection.create_index([("user_id", 1), ("created_at", -1)], name="notifications_user_created")
        notifications_collection.create_index([("user_id", 1), ("is_read", 1)], name="notifications_user_is_read")
        notifications_collection.create_index(
            [("created_at", 1)],
            name="notifications_ttl_120d",
            expireAfterSeconds=120 * 24 * 3600,
        )
    except PyMongoError as exc:
        logger.warning("Unable to create notifications indexes: %s", exc)

    try:
        likes_collection.create_index([("user_id", 1), ("note_id", 1)], unique=True, name="likes_user_note_uniq")
        likes_collection.create_index([("note_id", 1)], name="likes_note")
    except PyMongoError as exc:
        logger.warning("Unable to create likes indexes: %s", exc)

    try:
        leaderboard_collection.create_index([("user_id", 1), ("created_at", -1)], name="leaderboard_user_created")
        leaderboard_collection.create_index([("reason", 1), ("created_at", -1)], name="leaderboard_reason_created")
    except PyMongoError as exc:
        logger.warning("Unable to create leaderboard indexes: %s", exc)

    try:
        bookmarks_collection.create_index([("user_id", 1), ("note_id", 1)], unique=True, name="bookmarks_user_note_uniq")
        bookmarks_collection.create_index([("user_id", 1)], name="bookmarks_user")
    except PyMongoError as exc:
        logger.warning("Unable to create bookmarks indexes: %s", exc)

    try:
        comments_collection.create_index([("note_id", 1), ("created_at", -1)], name="comments_note_created")
        comments_collection.create_index([("parent_id", 1), ("created_at", 1)], name="comments_parent_created")
    except PyMongoError as exc:
        logger.warning("Unable to create comments indexes: %s", exc)

    try:
        comment_likes_collection.create_index(
            [("comment_id", 1), ("user_id", 1)],
            unique=True,
            name="comment_likes_comment_user_uniq",
        )
    except PyMongoError as exc:
        logger.warning("Unable to create comment likes indexes: %s", exc)

    try:
        reviews_collection.create_index([("note_id", 1), ("created_at", -1)], name="reviews_note_created")
        reviews_collection.create_index([("note_id", 1), ("user_id", 1)], unique=True, name="reviews_note_user_uniq")
    except PyMongoError as exc:
        logger.warning("Unable to create reviews indexes: %s", exc)

    try:
        requests_collection.create_index([("status", 1), ("created_at", -1)], name="requests_status_created")
    except PyMongoError as exc:
        logger.warning("Unable to create requests indexes: %s", exc)

    try:
        bundles_collection.create_index([("creator_id", 1), ("created_at", -1)], name="bundles_creator_created")
    except PyMongoError as exc:
        logger.warning("Unable to create bundles indexes: %s", exc)

    try:
        class_spaces_collection.create_index([("invite_code", 1)], unique=True, name="class_spaces_invite_code_uniq")
        class_spaces_collection.create_index([("dept", 1), ("semester", 1), ("section", 1)], name="class_spaces_dept_sem_section")
        class_spaces_collection.create_index([("created_by", 1)], name="class_spaces_created_by")
        space_memberships_collection.create_index([("space_id", 1), ("user_id", 1)], unique=True, name="space_memberships_space_user_uniq")
        space_memberships_collection.create_index([("user_id", 1)], name="space_memberships_user")
        space_memberships_collection.create_index([("space_id", 1), ("role", 1)], name="space_memberships_space_role")
        space_announcements_collection.create_index([("space_id", 1), ("created_at", -1)], name="space_announce_space_created")
        space_announcements_collection.create_index([("created_by", 1)], name="space_announce_created_by")
        space_notes_collection.create_index([("space_id", 1), ("note_id", 1)], unique=True, name="space_notes_space_note_uniq")
        space_notes_collection.create_index([("space_id", 1), ("shared_at", -1)], name="space_notes_space_shared_at")
    except PyMongoError as exc:
        logger.warning("Unable to create class spaces indexes: %s", exc)

    try:
        coupons_collection.create_index([("code", 1), ("seller_id", 1)], unique=True, name="coupons_code_seller_uniq")
        coupons_collection.create_index([("seller_id", 1), ("is_active", 1)], name="coupons_seller_active")
        campaigns_collection.create_index([("seller_id", 1), ("is_active", 1)], name="campaigns_seller_active")
        campaigns_collection.create_index([("note_id", 1), ("is_active", 1)], name="campaigns_note_active")
        creator_passes_collection.create_index([("seller_id", 1), ("is_active", 1)], name="creator_passes_seller_active")
        pass_subscriptions_collection.create_index(
            [("pass_id", 1), ("buyer_id", 1), ("status", 1)],
            name="pass_subscriptions_pass_buyer_status",
        )
        pass_subscriptions_collection.create_index(
            [("buyer_id", 1), ("status", 1), ("expires_at", -1)],
            name="pass_subscriptions_buyer_status_expires",
        )
        pass_subscriptions_collection.create_index(
            [("expires_at", 1)],
            name="pass_subscriptions_expires_ttl",
            expireAfterSeconds=0,
        )
    except PyMongoError as exc:
        logger.warning("Unable to create monetization indexes: %s", exc)

    try:
        college_domains_collection.create_index([("domain", 1)], unique=True, name="college_domains_domain_uniq")
        college_domains_collection.create_index([("college_id", 1)], name="college_domains_college_id")
        clusters_collection.create_index([("cluster_key", 1)], unique=True, sparse=True, name="clusters_cluster_key_uniq")
        clusters_collection.create_index([("university_type", 1), ("is_default", 1)], name="clusters_type_default")
        colleges_collection.create_index([("name", 1)], unique=True, name="colleges_name_uniq")
        cluster_inference_candidates_collection.create_index([("domain", 1)], unique=True, name="cluster_candidates_domain_uniq")
        cluster_inference_candidates_collection.create_index([("review_status", 1), ("updated_at", -1)], name="cluster_candidates_status_updated")
        request_pledges_collection.create_index([("request_id", 1), ("user_id", 1)], unique=True, name="request_pledges_request_user_uniq")
        request_pledges_collection.create_index([("request_id", 1), ("created_at", -1)], name="request_pledges_request_created")
        note_annotations_collection.create_index([("note_id", 1), ("user_id", 1)], unique=True, name="note_annotations_note_user_uniq")
        note_annotations_collection.create_index([("updated_at", -1)], name="note_annotations_updated")
        view_sessions_collection.create_index([("expires_at", 1)], name="view_sessions_expires_ttl", expireAfterSeconds=0)
    except PyMongoError as exc:
        logger.warning("Unable to create cluster/domain indexes: %s", exc)

    try:
        note_versions_collection.create_index([("note_id", 1), ("version_no", -1)], name="note_versions_note_version_no")
        seller_experiments_collection.create_index([("seller_id", 1), ("status", 1)], name="seller_experiments_seller_status")
        seller_experiments_collection.create_index([("seller_id", 1), ("created_at", -1)], name="seller_experiments_seller_created")
    except PyMongoError as exc:
        logger.warning("Unable to create note_versions/seller_experiments indexes: %s", exc)
