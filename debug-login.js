// Test login function - run this in browser console
async function testLogin() {
  try {
    console.log("Testing login...");
    
    const body = new URLSearchParams();
    body.append("username", "test@example.com");
    body.append("password", "test123");

    const response = await fetch("http://127.0.0.1:8001/auth/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: body,
    });
    
    console.log("Response status:", response.status);
    console.log("Response headers:", response.headers);
    
    const data = await response.json();
    console.log("Response data:", data);
    
    if (response.ok) {
      localStorage.setItem("token", data.access_token);
      console.log("Token saved:", data.access_token);
      
      // Test /auth/me
      const meResponse = await fetch("http://127.0.0.1:8001/auth/me", {
        headers: {
          "Authorization": `Bearer ${data.access_token}`
        }
      });
      
      const meData = await meResponse.json();
      console.log("User data:", meData);
    } else {
      console.error("Login failed:", data);
    }
  } catch (error) {
    console.error("Network error:", error);
  }
}

// Run test
testLogin();
