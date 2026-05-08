import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { registerUser } from "../api/client";

export default function RegisterForm() {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        name: "", user_name: "", business_name: "",
        email: "", mobile_no: "", password: "",
        review_link: "", business_desc: "", seo_keyword: "",
    });
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setLoading(true);
        const payload = {
            ...formData,
            seo_keyword: formData.seo_keyword.split(",").map(k => k.trim()).filter(Boolean),
        };
        try {
            await registerUser(payload);
            navigate("/login");
        } catch (err) {
            setError(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            {error && <div className="alert alert-error" style={{ marginBottom: "16px" }}>{error}</div>}

            <div className="form-row">
                <div className="form-group">
                    <label className="form-label">Full Name</label>
                    <input className="form-input" name="name" placeholder="John Doe"
                        value={formData.name} onChange={handleChange} required />
                </div>
                <div className="form-group">
                    <label className="form-label">Username</label>
                    <input className="form-input" name="user_name" placeholder="johndoe123"
                        value={formData.user_name} onChange={handleChange} required />
                </div>
            </div>

            <div className="form-group">
                <label className="form-label">Business Name</label>
                <input className="form-input" name="business_name" placeholder="Acme Corp"
                    value={formData.business_name} onChange={handleChange} required />
            </div>

            <div className="form-row">
                <div className="form-group">
                    <label className="form-label">Email</label>
                    <input className="form-input" name="email" type="email" placeholder="you@example.com"
                        value={formData.email} onChange={handleChange} required />
                </div>
                <div className="form-group">
                    <label className="form-label">Mobile Number</label>
                    <input className="form-input" name="mobile_no" placeholder="+1 234 567 890"
                        value={formData.mobile_no} onChange={handleChange} required />
                </div>
            </div>

            <div className="form-group">
                <label className="form-label">Password</label>
                <input className="form-input" name="password" type="password" placeholder="••••••••"
                    value={formData.password} onChange={handleChange} required />
            </div>

            <div className="form-group">
                <label className="form-label">Google Review Link</label>
                <input className="form-input" name="review_link" placeholder="https://g.page/review/..."
                    value={formData.review_link} onChange={handleChange} />
            </div>

            <div className="form-group">
                <label className="form-label">Business Description</label>
                <textarea className="form-textarea" name="business_desc"
                    placeholder="Briefly describe what your business does..."
                    value={formData.business_desc} onChange={handleChange} />
            </div>

            <div className="form-group">
                <label className="form-label">SEO Keywords <span style={{ color: "var(--text-3)", fontWeight: 400 }}>(comma separated)</span></label>
                <input className="form-input" name="seo_keyword" placeholder="preschool, education, daycare"
                    value={formData.seo_keyword} onChange={handleChange} />
            </div>

            <button className="btn-submit" type="submit" disabled={loading}>
                {loading ? <><span className="spinner" /> Creating account...</> : "Create Account →"}
            </button>
        </form>
    );
}
