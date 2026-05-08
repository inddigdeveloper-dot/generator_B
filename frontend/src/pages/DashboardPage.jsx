import { useState, useEffect } from "react";
import { useAuth } from "../hooks/useAuth";
import { getQRCode, updateUserProfile } from "../api/client"; 
import InddigLogo from "../components/InddigLogo";
import "../styles/Dashboard.css";

const LANGUAGES = ["English", "Hindi", "Hinglish"];
const TONES = ["Professional", "Friendly", "Enthusiastic"];

const STATS = [
    { icon: "⭐", bg: "rgba(59,130,246,0.15)", value: "0", label: "Reviews Generated" },
    { icon: "📈", bg: "rgba(34,211,238,0.15)", value: "—", label: "Avg Star Rating" },
    { icon: "🔗", bg: "rgba(244,114,182,0.15)", value: "0", label: "Review Link Clicks" },
    { icon: "🏆", bg: "rgba(16,185,129,0.15)", value: "0", label: "Keywords Ranked" },
];

export default function DashboardPage() {
    const { user } = useAuth();

    const [keywords, setKeywords] = useState(user?.seo_keyword?.join(", ") || "");
    const [language, setLanguage] = useState("English");
    const [tone, setTone] = useState("Professional");
    const [billItems, setBillItems] = useState("");
    const [qrSrc, setQrSrc] = useState(null);
    const [copied, setCopied] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    // Construct the URL to your platform's ReviewPage
    const internalReviewUrl = user?.user_name
        ? `${window.location.origin}/r/${user.user_name}`
        : "";

    useEffect(() => {
        if (!internalReviewUrl) return;
        // Try to get backend QR, fallback to public API using OUR internal URL
        getQRCode()
            .then(data => {
                if (data?.qr_code) setQrSrc(data.qr_code);
            })
            .catch(() => {
                setQrSrc(
                    `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(internalReviewUrl)}`
                );
            });
    }, [internalReviewUrl]);

    const handleCopy = () => {
        if (!internalReviewUrl) return;
        navigator.clipboard.writeText(internalReviewUrl).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            // Convert comma-separated string to an array for the backend
            const keywordArray = keywords.split(",").map(k => k.trim()).filter(Boolean);
            
            // Actually save the data to your database
            await updateUserProfile({
                seo_keyword: keywordArray,
                language: language,
                tone: tone,
                bill_items: billItems
            });
            
            setSaved(true);
            setTimeout(() => setSaved(false), 2500);
        } catch (error) {
            console.error("Failed to save settings:", error);
        } finally {
            setSaving(false);
        }
    };

    return (
        <div className="dashboard-page">
            <div className="bg-orbs">
                <div className="orb orb-1" style={{ opacity: 0.08 }} />
                <div className="orb orb-2" style={{ opacity: 0.07 }} />
            </div>

            <div className="dashboard-inner">

                {/* ── Header ── */}
                <div className="dashboard-header">
                    <div className="dashboard-greeting">Dashboard</div>
                    <h1 className="dashboard-title">
                        Welcome back, {user?.name?.split(" ")[0]} 👋
                    </h1>
                    <p className="dashboard-sub">
                        {user?.business_name
                            ? `Managing reviews for ${user.business_name}`
                            : "Here's your review performance overview"}
                    </p>
                </div>

                {/* ── Stats ── */}
                <div className="stats-grid">
                    {STATS.map(s => (
                        <div className="stat-card" key={s.label}>
                            <div className="stat-card-icon" style={{ background: s.bg }}>{s.icon}</div>
                            <div className="stat-card-value">{s.value}</div>
                            <div className="stat-card-label">{s.label}</div>
                        </div>
                    ))}
                </div>

                {/* ── Main layout ── */}
                <div className="dashboard-main">

                    {/* Left — Review QR card */}
                    <div className="review-card">
                        <div className="rc-logo-row">
                            <div>
                                <div className="rc-logo-name">inddig<span>media</span></div>
                                <div className="rc-logo-sub">AI-Powered Review Assistant</div>
                            </div>
                        </div>

                        <div className="rc-qr-area">
                            {/* FIXED: Using internalReviewUrl here instead of the undefined reviewUrl */}
                            {qrSrc || internalReviewUrl ? (
                                <img
                                    src={qrSrc || `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(internalReviewUrl)}`}
                                    alt="Review QR Code"
                                    className="rc-qr-img"
                                />
                            ) : (
                                <div className="rc-qr-placeholder">
                                    <span>📱</span>
                                    <p>Add your review link<br />to generate QR code</p>
                                </div>
                            )}
                        </div>

                        <p className="rc-scan-label">Scan to Leave a Review ⭐</p>
                        <div className="rc-biz-name">{user?.business_name || "Your Business"}</div>
                        <div className="rc-biz-sub">digital reviews</div>

                        <button
                            className={`rc-copy-btn${copied ? " rc-copy-btn--copied" : ""}`}
                            onClick={handleCopy}
                            disabled={!internalReviewUrl}
                        >
                            {copied ? "✓ Copied!" : "Copy Url 📋"}
                        </button>
                    </div>

                    {/* Right — Settings panel */}
                    <div className="settings-panel">

                        {/* Keywords */}
                        <div className="sp-section">
                            <label className="sp-label">Keywords</label>
                            <p className="sp-hint">Add at least 2–3 keywords for better ranking.</p>
                            <input
                                type="text"
                                className="sp-input"
                                placeholder="Enter keywords (comma separated)"
                                value={keywords}
                                onChange={e => setKeywords(e.target.value)}
                            />
                        </div>

                        {/* Language */}
                        <div className="sp-section">
                            <label className="sp-label">Choose Language</label>
                            <div className="sp-toggle-group">
                                {LANGUAGES.map(lang => (
                                    <button
                                        key={lang}
                                        className={`sp-toggle${language === lang ? " sp-toggle--on" : ""}`}
                                        onClick={() => setLanguage(lang)}
                                    >
                                        {lang}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Tone */}
                        <div className="sp-section">
                            <label className="sp-label">Default Tone</label>
                            <div className="sp-toggle-group">
                                {TONES.map(t => (
                                    <button
                                        key={t}
                                        className={`sp-toggle${tone === t ? " sp-toggle--on" : ""}`}
                                        onClick={() => setTone(t)}
                                    >
                                        {tone === t && <span className="sp-check">✓ </span>}
                                        {t}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Bill Items */}
                        <div className="sp-section">
                            <label className="sp-label">Bill Items</label>
                            <p className="sp-hint">Add bill items the AI will mention in reviews.</p>
                            <input
                                type="text"
                                className="sp-input"
                                placeholder="Enter items (comma separated)"
                                value={billItems}
                                onChange={e => setBillItems(e.target.value)}
                            />
                        </div>

                        {/* Save */}
                        <button
                            className="sp-save-btn btn btn-primary"
                            onClick={handleSave}
                            disabled={saving}
                        >
                            {saving ? (
                                <><span className="spinner" /> Saving…</>
                            ) : saved ? (
                                "✓ Saved!"
                            ) : (
                                "Save Settings"
                            )}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}