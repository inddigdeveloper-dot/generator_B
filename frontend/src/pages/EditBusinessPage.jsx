import { useState } from "react";
import { useAuth } from "../hooks/useAuth";
import { updateUserProfile } from "../api/client";
import "../styles/EditBusiness.css";

export default function EditBusinessPage() {
    const { user } = useAuth();

    const [form, setForm] = useState({
        business_name: user?.business_name || "",
        mobile_no:     user?.mobile_no     || "",
        review_link:   user?.review_link   || "",
        seo_keyword:   user?.seo_keyword?.join(", ") || "",
    });
    const [saving,  setSaving]  = useState(false);
    const [success, setSuccess] = useState("");
    const [error,   setError]   = useState("");

    const handleChange = e => {
        setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
        setSuccess("");
        setError("");
    };

    const handleSubmit = async e => {
        e.preventDefault();
        setSaving(true);
        setSuccess("");
        setError("");
        try {
            const payload = {
                ...form,
                seo_keyword: form.seo_keyword
                    .split(",")
                    .map(k => k.trim())
                    .filter(Boolean),
            };
            await updateUserProfile(payload);
            setSuccess("Business profile updated successfully!");
        } catch (err) {
            setError(typeof err === "string" ? err : "Failed to update profile.");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="inner-page">
            <div className="bg-orbs">
                <div className="orb orb-1" style={{ opacity: 0.07 }} />
                <div className="orb orb-2" style={{ opacity: 0.06 }} />
            </div>

            <div className="inner-page-body">
                <div className="page-header">
                    <div className="page-eyebrow">Edit Business</div>
                    <h1 className="page-title">Business Profile</h1>
                    <p className="page-sub">Update your business details used for AI review generation.</p>
                </div>

                <div className="eb-layout">
                    <form className="panel eb-form" onSubmit={handleSubmit}>
                        <div className="panel-header">
                            <span className="panel-title">Business Details</span>
                        </div>

                        {success && <div className="alert alert-success">{success}</div>}
                        {error   && <div className="alert alert-error">{error}</div>}

                        <div className="form-group">
                            <label className="form-label">Business Name</label>
                            <input
                                type="text"
                                name="business_name"
                                className="form-input"
                                placeholder="Your business name"
                                value={form.business_name}
                                onChange={handleChange}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Mobile Number</label>
                            <input
                                type="tel"
                                name="mobile_no"
                                className="form-input"
                                placeholder="+91 XXXXX XXXXX"
                                value={form.mobile_no}
                                onChange={handleChange}
                            />
                        </div>

                        <div className="form-group">
                            <label className="form-label">Google Review Link</label>
                            <input
                                type="url"
                                name="review_link"
                                className="form-input"
                                placeholder="https://g.page/r/your-review-link"
                                value={form.review_link}
                                onChange={handleChange}
                            />
                            <p className="eb-field-hint">Customers will be sent to this link to leave a review.</p>
                        </div>

                        <div className="form-group">
                            <label className="form-label">SEO Keywords</label>
                            <input
                                type="text"
                                name="seo_keyword"
                                className="form-input"
                                placeholder="e.g. digital marketing, social media, branding"
                                value={form.seo_keyword}
                                onChange={handleChange}
                            />
                            <p className="eb-field-hint">Comma-separated keywords the AI will include in reviews.</p>
                        </div>

                        <button
                            type="submit"
                            className="btn btn-primary eb-save-btn"
                            disabled={saving}
                        >
                            {saving ? <><span className="spinner" /> Saving…</> : "Save Changes"}
                        </button>
                    </form>

                    {/* Info sidebar */}
                    <div className="eb-info">
                        <div className="panel">
                            <div className="panel-header">
                                <span className="panel-title">Account Info</span>
                            </div>
                            <div className="eb-info-item">
                                <span className="eb-info-label">Email</span>
                                <span className="eb-info-value">{user?.email || "—"}</span>
                            </div>
                            <div className="eb-info-item">
                                <span className="eb-info-label">Account Name</span>
                                <span className="eb-info-value">{user?.name || "—"}</span>
                            </div>
                            <div className="eb-info-item">
                                <span className="eb-info-label">Plan</span>
                                <span className="eb-info-value eb-plan-tag">Free</span>
                            </div>
                        </div>

                        <div className="panel eb-tip">
                            <div className="eb-tip-icon">💡</div>
                            <p>Add 2–3 targeted keywords to help the AI generate reviews that boost your local SEO ranking.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
