# Notes Market - Full Stack Application

A comprehensive notes marketplace platform with user authentication, content management, and monetization features.

## 🚀 Features

### Core Features
- **User Authentication** - Signup, login, role-based access (student, moderator, admin)
- **Note Management** - Upload, browse, search, and filter notes by subject, department, semester
- **Purchase System** - Buy and sell notes with secure payment integration
- **Bookmarking** - Save favorite notes for later access
- **Likes System** - Like and unlike notes with real-time updates

### Advanced Features
- **Reviews & Ratings** - 5-star rating system with comments and verified purchase badges
- **Report System** - Report inappropriate content with admin moderation
- **Dispute/Refund** - Raise disputes for purchased notes with admin resolution
- **Verified Sellers** - Seller verification system for premium content
- **Trending Algorithm** - Popular content discovery based on views and engagement
- **Seller Dashboard** - Analytics for sellers with earnings and sales tracking

### Admin Features
- **Content Moderation** - Approve/reject uploaded notes
- **User Management** - Manage users, roles, and permissions
- **Seller Verification** - Verify sellers for paid content upload
- **Report Management** - Handle user reports and disputes
- **Analytics** - Track platform usage and performance

## 🛠 Technology Stack

### Backend
- **FastAPI** - Modern Python web framework
- **MongoDB** - NoSQL database for flexible data storage
- **JWT Authentication** - Secure token-based authentication
- **Bcrypt** - Password hashing and security
- **Pydantic** - Data validation and serialization

### Frontend
- **React 19** - Modern React with latest features
- **React Router** - Client-side routing
- **Tailwind CSS** - Utility-first CSS framework
- **Axios** - HTTP client for API requests
- **React Hot Toast** - Beautiful toast notifications

### Development Tools
- **Vite** - Fast development build tool
- **ESLint** - Code linting and quality
- **Hot Module Replacement** - Instant development feedback

## 📁 Project Structure

```
Notes Market/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── routes/            # API endpoints
│   │   ├── models/            # Data models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic
│   │   ├── utils/             # Utilities
│   │   └── database.py        # MongoDB connection
│   ├── uploads/               # File uploads
│   └── main.py               # FastAPI app entry
├── notes-frontend/            # React frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/            # Page components
│   │   ├── auth/             # Authentication context
│   │   ├── api/              # API client
│   │   └── main.jsx          # React app entry
│   ├── public/               # Static assets
│   └── package.json          # Dependencies
└── README.md                 # This file
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- MongoDB (local or Atlas)

### One-Command Local Run
```bash
npm run dev:up
```

This starts MongoDB, backend, and frontend together with local-safe defaults:
- `JWT_SECRET_KEY=dev-local-secret` (if not already set)
- `MODERATION_AI_MODE=gemini` (uses `GEMINI_API_KEY` from `backend/.env` if set)
- MongoDB data is always stored in one fixed folder:
  - `/Users/aldricanto/Documents/Notes market/.run/mongodb`

To stop everything:
```bash
npm run dev:down
```

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python migrations/apply_indexes.py
uvicorn app.main:app --reload --port 8001
```

In another terminal for AI job processing:
```bash
cd backend
python run_ai_worker.py
```

### Frontend Setup
```bash
cd notes-frontend
npm install
npm run dev -- --host
```

### Access Points
- **Frontend**: http://localhost:5173
- **Backend API**: http://127.0.0.1:8001
- **API Documentation**: http://127.0.0.1:8001/docs

## 📚 API Endpoints

### Authentication
- `POST /auth/signup` - User registration
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user

### Notes
- `GET /notes` - Browse notes with filters
- `POST /notes` - Upload new note
- `GET /notes/{id}/details` - Get note details
- `GET /notes/trending` - Get trending notes

### Reviews
- `POST /reviews/note/{id}` - Add review
- `GET /reviews/note/{id}` - Get note reviews
- `GET /reviews/note/{id}/summary` - Get review summary

### Reports & Disputes
- `POST /reports/note/{id}` - Report note
- `POST /disputes/note/{id}` - Raise dispute
- `GET /reports/pending` - Get pending reports (admin)
- `GET /disputes/pending` - Get pending disputes (admin)

### Seller Analytics
- `GET /seller/dashboard` - Get seller statistics

## 🔐 Security Features

- JWT-based authentication
- HttpOnly auth cookies (frontend does not store JWT in localStorage)
- Role-based access control
- Input validation and sanitization
- Redis-backed rate limiting on sensitive endpoints (with local fallback)
- Secure file upload with validation
- Password hashing with bcrypt

## 🎨 UI/UX Features

- Modern dark theme design
- Responsive layout for all devices
- Real-time updates with hot reload
- Loading states and error handling
- Toast notifications for user feedback
- Smooth animations and transitions

## 📊 Analytics & Monitoring

- View tracking for trending algorithm
- User engagement metrics
- Sales and earnings tracking
- Content performance analytics
- Report and dispute statistics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- FastAPI team for the excellent framework
- React team for the amazing library
- Tailwind CSS for the utility-first CSS framework
- MongoDB for the flexible database solution
