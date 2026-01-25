import time

# user_id -> [timestamps]
USER_REQUESTS = {}

MAX_REQUESTS_PER_MINUTE = 15


def check_rate_limit(user_id: str):
    now = time.time()
    window_start = now - 60

    if user_id not in USER_REQUESTS:
        USER_REQUESTS[user_id] = []

    # keep only last 60s hits
    USER_REQUESTS[user_id] = [t for t in USER_REQUESTS[user_id] if t > window_start]

    if len(USER_REQUESTS[user_id]) >= MAX_REQUESTS_PER_MINUTE:
        return False

    USER_REQUESTS[user_id].append(now)
    return True
