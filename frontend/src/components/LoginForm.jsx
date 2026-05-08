import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser } from "../api/client";
import { useAuth } from "../hooks/useAuth";

export default function LoginForm() {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [formData, setFormData] = useState({ login_id: "", password: "" });
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        try {
            const result = await loginUser(formData);
            await login(result.access_token, result.refresh_token);
            navigate("/dashboard");
        } catch (err) {
            setError(typeof err === "string" ? err : "Login failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-error" style={{ marginBottom: "16px" }}>{error}</div>}

            <div className="form-group">
                <label className="form-label">Email / Username / Mobile</label>
                <input
                    className="form-input"
                    name="login_id"
                    type="text"
                    placeholder="Enter your email, username, or mobile"
                    value={formData.login_id}
                    onChange={handleChange}
                    required
                />
            </div>

            <div className="form-group">
                <label className="form-label">Password</label>
                <input
                    className="form-input"
                    name="password"
                    type="password"
                    placeholder="••••••••"
                    value={formData.password}
                    onChange={handleChange}
                    required
                />
            </div>

            <button className="btn-submit" type="submit" disabled={loading}>
                {loading ? <><span className="spinner" /> Signing in...</> : "Sign In"}
            </button>
        </form>
    );
}
