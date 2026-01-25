import { BrowserRouter, Routes, Route } from "react-router-dom";
import Signup from "./pages/Signup";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import UploadNote from "./pages/UploadNote";
import Leaderboard from "./pages/Leaderboard";
import Moderation from "./pages/Moderation";
import MyUploads from "./pages/MyUploads";
import MyBookmarks from "./pages/MyBookmarks";
import MyPurchases from "./pages/MyPurchases";
import Viewer from "./pages/Viewer";
import NoteDetails from "./pages/NoteDetails";
import Trending from "./pages/Trending";
import SellerDashboard from "./pages/SellerDashboard";
import ProtectedRoute from "./auth/ProtectedRoute";

console.log("App.jsx loaded");

export default function App() {
  console.log("App component rendering");
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Signup />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/upload"
          element={
            <ProtectedRoute>
              <UploadNote />
            </ProtectedRoute>
          }
        />

        <Route
          path="/leaderboard"
          element={
            <ProtectedRoute>
              <Leaderboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/moderation"
          element={
            <ProtectedRoute>
              <Moderation />
            </ProtectedRoute>
          }
        />

        <Route
          path="/my-uploads"
          element={
            <ProtectedRoute>
              <MyUploads />
            </ProtectedRoute>
          }
        />

        <Route
          path="/my-bookmarks"
          element={
            <ProtectedRoute>
              <MyBookmarks />
            </ProtectedRoute>
          }
        />

        <Route
          path="/my-purchases"
          element={
            <ProtectedRoute>
              <MyPurchases />
            </ProtectedRoute>
          }
        />

        <Route
          path="/notes/:noteId"
          element={
            <ProtectedRoute>
              <NoteDetails />
            </ProtectedRoute>
          }
        />

        <Route
          path="/trending"
          element={
            <ProtectedRoute>
              <Trending />
            </ProtectedRoute>
          }
        />

        <Route
          path="/seller-dashboard"
          element={
            <ProtectedRoute>
              <SellerDashboard />
            </ProtectedRoute>
          }
        />

        <Route
          path="/viewer"
          element={
            <ProtectedRoute>
              <Viewer />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
