import { useState, useEffect } from "react";
import { useAuth } from "../hooks/useAuth";
import { getQRCode, getReviewStats, updateUserProfile } from "../api/client";
import "../styles/Dashboard.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const LANGUAGES = ["English", "Hindi", "Hinglish"];
const TONES     = ["Professional", "Friendly", "Enthusiastic"];

export default function DashboardPage() {
    const { user, login } = useAuth();

    const [keywords,  setKeywords]  = useState(user?.seo_keyword?.join(", ") || "");
    const [language,  setLanguage]  = useState(user?.language  || "English");
    const [tone,      setTone]      = useState(user?.tone       || "Professional");
    const [billItems, setBillItems] = useState(user?.bill_items || "");
    const [qrSrc,     setQrSrc]     = useState(null);
    const [copied,    setCopied]    = useState(false);
    const [saving,    setSaving]    = useState(false);
    const [saved,     setSaved]     = useState(false);
    const [saveError, setSaveError] = useState("");

    const [stats, setStats] = useState({ total_reviews: null, avg_rating: null, this_month: null });

    const reviewUrl = user?.user_name
        ? `${window.location.origin}/r/${user.user_name}`
        : "";

    useEffect(() => {
        if (!reviewUrl) return;
        getQRCode()
            .then(d => { if (d?.qr_code_url) setQrSrc(`${API_URL}${d.qr_code_url}`); })
            .catch(() => {
                setQrSrc(`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(reviewUrl)}`);
            });
    }, [reviewUrl]);

    useEffect(() => {
        getReviewStats().then(setStats).catch(() => {});
    }, []);

    const statCards = [
        { icon: "📝", label: "Reviews Generated", value: stats.total_reviews ?? "—", color: "#3b82f6" },
        { icon: "⭐", label: "Avg Star Rating",    value: stats.avg_rating != null ? stats.avg_rating.toFixed(1) : "—", color: "#f59e0b" },
        { icon: "📅", label: "This Month",         value: stats.this_month ?? "—", color: "#ec4899" },
        { icon: "🏷️", label: "Keywords",           value: user?.seo_keyword?.length ?? 0, color: "#10b981" },
    ];

    const handleCopy = () => {
        if (!reviewUrl) return;
        navigator.clipboard.writeText(reviewUrl).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    const handleSave = async () => {
        setSaving(true);
        setSaveError("");
        try {
            const keywordArray = keywords.split(",").map(k => k.trim()).filter(Boolean);
            await updateUserProfile({ seo_keyword: keywordArray, language, tone, bill_items: billItems });
            const token   = localStorage.getItem("token");
            const refresh = localStorage.getItem("refresh_token");
            if (token && refresh) await login(token, refresh);
            setSaved(true);
            setTimeout(() => setSaved(false), 2500);
        } catch (err) {
            setSaveError(typeof err === "string" ? err : "Failed to save. Please try again.");
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="dashboard-page">
            <div className="bg-orbs" aria-hidden>
                <div className="orb orb-1" style={{ opacity: 0.07 }} />
                <div className="orb orb-2" style={{ opacity: 0.06 }} />
            </div>

            <div className="dashboard-inner">

                {/* ── Page header ── */}
                <div className="dash-head">
                    <div>
                        <p className="dash-eyebrow">Dashboard</p>
                        <h1 className="dash-title">Welcome back, {user?.name?.split(" ")[0]}</h1>
                        <p className="dash-sub">
                            {user?.business_name ? `Managing reviews for ${user.business_name}` : "Set up your business profile to start generating reviews"}
                        </p>
                    </div>
                </div>

                {/* ── Stat row ── */}
                <div className="dash-stats">
                    {statCards.map(s => (
                        <div className="dash-stat" key={s.label}>
                            <div className="dash-stat-icon" style={{ background: s.color + "1a" }}>
                                <span>{s.icon}</span>
                            </div>
                            <div>
                                <div className="dash-stat-value">{String(s.value)}</div>
                                <div className="dash-stat-label">{s.label}</div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* ── Main two-column ── */}
                <div className="dash-main">

                    {/* ── Left: QR card ── */}
                    <div className="qr-card">
                        {/* Header strip */}
                        <div className="qr-card-header">
                            <div className="qr-brand">
                                <span className="qr-brand-ind">inddig</span><span className="qr-brand-med">media</span>
                            </div>
                            <div className="qr-brand-tag">AI Review Assistant</div>
                        </div>

                        {/* QR image */}
                        <div className="qr-image-wrap">
                            {qrSrc || reviewUrl ? (
                                <img
                                    src={qrSrc || `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(reviewUrl)}`}
                                    alt="Review QR Code"
                                    className="qr-image"
                                />
                            ) : (
                                <div className="qr-empty">
                                    <span>📱</span>
                                    <p>Add a Google Place ID<br />to generate your QR</p>
                                </div>
                            )}
                            <div className="qr-corner qr-corner-tl" />
                            <div className="qr-corner qr-corner-tr" />
                            <div className="qr-corner qr-corner-bl" />
                            <div className="qr-corner qr-corner-br" />
                        </div>

                        <p className="qr-scan-hint">Scan to leave a review</p>

                        {/* Business info strip */}
                        <div className="qr-biz-strip">
                            <div className="qr-biz-name">{user?.business_name || "Your Business"}</div>
                            <div className="qr-biz-tag">Google Review</div>
                        </div>

                        {/* URL + copy */}
                        <div className="qr-url-row">
                            <span className="qr-url-text">{reviewUrl || "—"}</span>
                            <button
                                className={`qr-copy-btn${copied ? " qr-copy-btn--ok" : ""}`}
                                onClick={handleCopy}
                                disabled={!reviewUrl}
                            >
                                {copied ? "✓" : "Copy"}
                            </button>
                        </div>
                    </div>

                    {/* ── Right: Settings panel ── */}
                    <div className="settings-card">
                        <div className="settings-card-head">
                            <h2 className="settings-card-title">Review Settings</h2>
                            <p className="settings-card-sub">These are used by the AI when generating reviews.</p>
                        </div>

                        <div className="settings-body">

                            <div className="field-group">
                                <label className="field-label">SEO Keywords</label>
                                <p className="field-hint">Comma-separated — the AI weaves these into reviews naturally.</p>
                                <input
                                    className="field-input"
                                    placeholder="e.g. digital marketing, SEO, branding"
                                    value={keywords}
                                    onChange={e => setKeywords(e.target.value)}
                                />
                            </div>

                            <div className="field-group">
                                <label className="field-label">Language</label>
                                <div className="toggle-row">
                                    {LANGUAGES.map(l => (
                                        <button
                                            key={l}
                                            className={`toggle-btn${language === l ? " toggle-btn--on" : ""}`}
                                            onClick={() => setLanguage(l)}
                                        >{l}</button>
                                    ))}
                                </div>
                            </div>

                            <div className="field-group">
                                <label className="field-label">Default Tone</label>
                                <div className="toggle-row">
                                    {TONES.map(t => (
                                        <button
                                            key={t}
                                            className={`toggle-btn${tone === t ? " toggle-btn--on" : ""}`}
                                            onClick={() => setTone(t)}
                                        >{t}</button>
                                    ))}
                                </div>
                            </div>

                            <div className="field-group">
                                <label className="field-label">Bill Items</label>
                                <p className="field-hint">Products or services the AI can mention in reviews.</p>
                                <input
                                    className="field-input"
                                    placeholder="e.g. website design, SEO audit, logo"
                                    value={billItems}
                                    onChange={e => setBillItems(e.target.value)}
                                />
                            </div>

                            {saveError && <div className="alert alert-error">{saveError}</div>}

                            <button
                                className={`save-btn btn btn-primary${saved ? " save-btn--saved" : ""}`}
                                onClick={handleSave}
                                disabled={saving}
                            >
                                {saving ? <><span className="spinner" /> Saving…</>
                                 : saved ? "✓ Saved!"
                                 : "Save Settings"}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
