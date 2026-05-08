import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import { GoogleOAuthProvider } from "@react-oauth/google";
import { AuthProvider } from "./context/AuthContext.jsx";
import ProtectedRoute from "./components/ProtectedRoute";
import Navbar from "./components/Navbar";
import LandingPage from "./pages/LandingPage";
import RegisterPage from "./pages/RegisterPage";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import SmartReplyPage from "./pages/SmartReplyPage";
import PricingPage from "./pages/PricingPage";
import EditBusinessPage from "./pages/EditBusinessPage";
import OrderHistoryPage from "./pages/OrderHistoryPage";
import ReviewPage from "./pages/ReviewPage";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

function AppContent() {
    const location = useLocation();
    const showNavbar = !location.pathname.startsWith("/r/");

    return (
        <>
            {showNavbar && <Navbar />}
            <Routes>
                {/* Public customer review page — no auth, no navbar */}
                <Route path="/r/:username" element={<ReviewPage />} />

                <Route path="/"         element={<LandingPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/login"    element={<LoginPage />} />
                <Route path="/pricing"  element={<PricingPage />} />

                <Route path="/dashboard" element={
                    <ProtectedRoute><DashboardPage /></ProtectedRoute>
                } />
                <Route path="/smart-reply" element={
                    <ProtectedRoute><SmartReplyPage /></ProtectedRoute>
                } />
                <Route path="/edit-business" element={
                    <ProtectedRoute><EditBusinessPage /></ProtectedRoute>
                } />
                <Route path="/order-history" element={
                    <ProtectedRoute><OrderHistoryPage /></ProtectedRoute>
                } />
            </Routes>
        </>
    );
}

export default function App() {
    return (
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
            <AuthProvider>
                <BrowserRouter>
                    <AppContent />
                </BrowserRouter>
            </AuthProvider>
        </GoogleOAuthProvider>
    );
}
