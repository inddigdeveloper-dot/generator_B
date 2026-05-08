import { Link } from "react-router-dom";
import LoginForm from "../components/LoginForm";
import GoogleLoginButton from "../components/GoogleLoginButton";
import InddigLogo from "../components/InddigLogo";
import "../styles/AuthPage.css";

export default function LoginPage() {
    return (
        <div className="auth-page">
            <div className="bg-orbs">
                <div className="orb orb-1" />
                <div className="orb orb-2" />
                <div className="orb orb-3" />
            </div>

            <div className="auth-card">
                <Link to="/" className="auth-logo">
                    <InddigLogo size={100} />
                    {/* <span className="auth-logo-text">inddig<span>media</span></span> */}
                </Link>

                <div className="auth-header">
                    <div className="auth-title">Welcome back</div>
                    <div className="auth-sub">Sign in to your account to continue</div>
                </div>

                <LoginForm />

                <div className="auth-divider">or</div>

                <GoogleLoginButton />

                <div className="auth-footer">
                    Don&apos;t have an account?{" "}
                    <Link to="/register">Create one free</Link>
                </div>
            </div>
        </div>
    );
}
