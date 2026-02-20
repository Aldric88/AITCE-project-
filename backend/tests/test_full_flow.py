import requests
import time
import os
import pytest

BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8001")

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LIVE_API_TESTS", "0") != "1",
    reason="Live API tests are disabled. Set RUN_LIVE_API_TESTS=1 to run.",
)

def test_full_flow():
    print("🚀 Starting Full System Test...")
    
    # 1. Public Feed (Should work without Auth)
    print("\n1. Testing Public Feed...")
    res = requests.get(f"{BASE_URL}/notes/")
    if res.status_code == 200:
        print("✅ Public Feed Accessible")
    else:
        print(f"❌ Public Feed Failed: {res.status_code} {res.text}")
        return

    # 2. Signup User A (PSG)
    email_a = f"test_a_{int(time.time())}@psgtech.ac.in"
    password = "password123"
    print(f"\n2. Registering User A ({email_a})...")
    
    res = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": email_a,
        "password": password,
        "name": "User A",
        "dept": "CSE",
        "year": 3,
        "section": "A"
    })
    if res.status_code == 200:
        print("✅ User A Signed Up")
    else:
        print(f"❌ Signup Failed: {res.text}")
        # proceed if user already exists
        
    # 3. Login User A
    print("3. Logging in User A...")
    res = requests.post(f"{BASE_URL}/auth/login", data={
        "username": email_a,
        "password": password
    })
    if res.status_code != 200:
        print(f"❌ Login Failed: {res.text}")
        return
        
    token_a = res.json()["access_token"]
    print("✅ User A Logged In")
    
    headers_a = {"Authorization": f"Bearer {token_a}"}
    
    # 4. Upload Note (User A)
    print("\n4. User A Uploading Note...")
    # First need a file
    # We can fake the upload flow or just note creation if we mock file_url.
    # But backend checks file_url existence. 
    # Let's try to upload a dummy file first? 
    # The file upload endpoint is likely /files/upload/ or similar?
    # Checking file_routes.py would be good, but let's assume we can't easily upload in this script without multipart.
    # We can try to create a note with a fake file_url and expect failure, OR 
    # create a 'text' note or 'link' note which doesn't require file upload?
    # Note Create schema: link note requires external_link
    
    note_data = {
        "title": "Test Link Note",
        "description": "Testing link note",
        "dept": "CSE",
        "semester": 5,
        "subject": "OS",
        "unit": "1",
        "note_type": "link",
        "external_link": "http://google.com",
        "tags": ["test"],
        "is_paid": False
    }
    
    res = requests.post(f"{BASE_URL}/notes/", json=note_data, headers=headers_a)
    if res.status_code == 200:
        print("✅ Note Uploaded (Pending)")
        note_id = res.json()["id"]
    else:
        print(f"❌ Note Upload Failed: {res.text}")
        return

    # 5. Check My Notes
    print("\n5. Checking My Notes...")
    res = requests.get(f"{BASE_URL}/notes/my", headers=headers_a)
    if res.status_code == 200 and len(res.json()) > 0:
        print("✅ My Notes Fetched")
    else:
        print(f"❌ My Notes Failed: {res.text}")

    # 6. Rate Limit Test (Login spam)
    print("\n6. Testing Rate Limiting (Login)...")
    spam_count = 0
    for i in range(10):
        res = requests.post(f"{BASE_URL}/auth/login", data={
            "username": email_a,
            "password": "wrongpassword"
        })
        if res.status_code == 429:
            print("✅ Rate Limit Triggered (429 Too Many Requests)")
            break
        spam_count += 1
    
    if spam_count == 10:
        print("❌ Rate Limit Failed to Trigger")

    print("\n✅ Full Flow Test Completed.")

if __name__ == "__main__":
    test_full_flow()
