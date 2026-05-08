import { Link } from "react-router-dom";
import RegisterForm from "../components/RegisterForm";
import InddigLogo from "../components/InddigLogo";
import "../styles/AuthPage.css";

export default function RegisterPage() {
    return (
        <div className="auth-page">
            <div className="bg-orbs">
                <div className="orb orb-1" />
                <div className="orb orb-2" />
                <div className="orb orb-3" />
            </div>

            <div className="auth-card auth-card-wide">
                <Link to="/" className="auth-logo">
                    <InddigLogo size={100} />
                    {/* <span className="auth-logo-text">inddig<span>media</span></span> */}
                </Link>

                <div className="auth-header">
                    <div className="auth-title">Create your account</div>
                    <div className="auth-sub">Start generating reviews for your business today</div>
                </div>

                <RegisterForm />

                <div className="auth-footer">
                    Already have an account?{" "}
                    <Link to="/login">Sign in</Link>
                </div>
            </div>
        </div>
    );
}
