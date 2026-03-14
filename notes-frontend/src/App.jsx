import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ProtectedRoute from "./auth/ProtectedRoute";

const Signup = lazy(() => import("./pages/Signup"));
const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const UploadNote = lazy(() => import("./pages/UploadNote"));
const Leaderboard = lazy(() => import("./pages/Leaderboard"));
const ModerationPanel = lazy(() => import("./pages/ModerationPanel"));
const RejectedNotes = lazy(() => import("./pages/RejectedNotes"));
const ModerationDashboard = lazy(() => import("./pages/ModerationDashboard"));
const Requests = lazy(() => import("./pages/Requests"));
const Bundles = lazy(() => import("./pages/Bundles"));
const VerifyEmail = lazy(() => import("./pages/VerifyEmail"));
const FollowingFeed = lazy(() => import("./pages/FollowingFeed"));
const Profile = lazy(() => import("./pages/Profile"));
const CreatorProfile = lazy(() => import("./pages/CreatorProfile"));
const TopCreators = lazy(() => import("./pages/TopCreators"));
const Notifications = lazy(() => import("./pages/Notifications"));
const SecureViewer = lazy(() => import("./pages/SecureViewer"));
const OpsDashboard = lazy(() => import("./pages/OpsDashboard"));
const ClassSpaces = lazy(() => import("./pages/ClassSpaces"));
const Monetization = lazy(() => import("./pages/Monetization"));
const AdminAnalytics = lazy(() => import("./pages/AdminAnalytics"));
const AdminDomainCandidates = lazy(() => import("./pages/AdminDomainCandidates"));
const Wallet = lazy(() => import("./pages/Wallet"));
const MyUploads = lazy(() => import("./pages/MyUploads"));
const MyBookmarks = lazy(() => import("./pages/MyBookmarks"));
const MyPurchases = lazy(() => import("./pages/MyPurchases"));
const Viewer = lazy(() => import("./pages/Viewer"));
const NoteDetails = lazy(() => import("./pages/NoteDetails"));
const Trending = lazy(() => import("./pages/Trending"));
const SellerDashboard = lazy(() => import("./pages/SellerDashboard"));
const Passes = lazy(() => import("./pages/Passes"));
const MyLibrary = lazy(() => import("./pages/MyLibrary"));

function Protected(element) {
  return <ProtectedRoute>{element}</ProtectedRoute>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="p-6 text-sm font-bold uppercase text-gray-500">Loading...</div>}>
        <Routes>
          <Route path="/" element={<Signup />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={Protected(<Dashboard />)} />
          <Route path="/upload" element={Protected(<UploadNote />)} />
          <Route path="/upload-note" element={Protected(<UploadNote />)} />
          <Route path="/leaderboard" element={Protected(<Leaderboard />)} />
          <Route path="/moderation" element={Protected(<ModerationPanel />)} />
          <Route path="/moderation-dashboard" element={Protected(<ModerationDashboard />)} />
          <Route path="/rejected-notes" element={Protected(<RejectedNotes />)} />
          <Route path="/my-uploads" element={Protected(<MyUploads />)} />
          <Route path="/my-library" element={Protected(<MyLibrary />)} />
          <Route path="/my-bookmarks" element={Protected(<MyBookmarks />)} />
          <Route path="/my-purchases" element={Protected(<MyPurchases />)} />
          <Route path="/wallet" element={Protected(<Wallet />)} />
          <Route path="/notes/:noteId" element={Protected(<NoteDetails />)} />
          <Route path="/trending" element={Protected(<Trending />)} />
          <Route path="/seller-dashboard" element={Protected(<SellerDashboard />)} />
          <Route path="/requests" element={Protected(<Requests />)} />
          <Route path="/bundles" element={Protected(<Bundles />)} />
          <Route path="/spaces" element={Protected(<ClassSpaces />)} />
          <Route path="/monetization" element={Protected(<Monetization />)} />
          <Route path="/admin-analytics" element={Protected(<AdminAnalytics />)} />
          <Route path="/admin-domain-candidates" element={Protected(<AdminDomainCandidates />)} />
          <Route path="/verify-email" element={Protected(<VerifyEmail />)} />
          <Route path="/following" element={Protected(<FollowingFeed />)} />
          <Route path="/profile" element={Protected(<Profile />)} />
          <Route path="/creator/:creatorId" element={Protected(<CreatorProfile />)} />
          <Route path="/top-creators" element={Protected(<TopCreators />)} />
          <Route path="/notifications" element={Protected(<Notifications />)} />
          <Route path="/ops-dashboard" element={Protected(<OpsDashboard />)} />
          <Route path="/secure-viewer/:noteId" element={Protected(<SecureViewer />)} />
          <Route path="/viewer" element={Protected(<Viewer />)} />
          <Route path="/passes" element={Protected(<Passes />)} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
