import { useState } from "react";
import "../styles/SmartReply.css";

const TONES     = ["Professional", "Friendly", "Enthusiastic"];
const LANGUAGES = ["English", "Hindi", "Hinglish"];

export default function SmartReplyPage() {
    const [review,   setReview]   = useState("");
    const [tone,     setTone]     = useState("Professional");
    const [language, setLanguage] = useState("English");
    const [reply,    setReply]    = useState("");
    const [loading,  setLoading]  = useState(false);
    const [copied,   setCopied]   = useState(false);

    const handleGenerate = async () => {
        if (!review.trim()) return;
        setLoading(true);
        setReply("");
        await new Promise(r => setTimeout(r, 1200));
        setReply(
            `Thank you so much for your wonderful review! We truly appreciate you taking the time to share your experience with us. Your kind words motivate our entire team to keep delivering the best service possible. We look forward to serving you again soon! 🙏`
        );
        setLoading(false);
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(reply).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    };

    return (
        <div className="inner-page">
            <div className="bg-orbs">
                <div className="orb orb-1" style={{ opacity: 0.07 }} />
                <div className="orb orb-2" style={{ opacity: 0.06 }} />
            </div>

            <div className="inner-page-body">
                <div className="page-header">
                    <div className="page-eyebrow">Smart Reply</div>
                    <h1 className="page-title">AI Review Reply Generator</h1>
                    <p className="page-sub">Paste a customer review and get a professional AI-crafted reply in seconds.</p>
                </div>

                <div className="sr-layout">
                    {/* Input panel */}
                    <div className="panel">
                        <div className="panel-header">
                            <span className="panel-title">Customer Review</span>
                        </div>

                        <textarea
                            className="sr-textarea"
                            placeholder="Paste the customer review here…"
                            value={review}
                            onChange={e => setReview(e.target.value)}
                            rows={5}
                        />

                        <div className="sr-controls">
                            <div className="sr-control-group">
                                <label className="sp-label">Language</label>
                                <div className="sp-toggle-group">
                                    {LANGUAGES.map(l => (
                                        <button
                                            key={l}
                                            className={`sp-toggle${language === l ? " sp-toggle--on" : ""}`}
                                            onClick={() => setLanguage(l)}
                                        >
                                            {l}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="sr-control-group">
                                <label className="sp-label">Tone</label>
                                <div className="sp-toggle-group">
                                    {TONES.map(t => (
                                        <button
                                            key={t}
                                            className={`sp-toggle${tone === t ? " sp-toggle--on" : ""}`}
                                            onClick={() => setTone(t)}
                                        >
                                            {t}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <button
                            className="btn btn-primary sr-generate-btn"
                            onClick={handleGenerate}
                            disabled={loading || !review.trim()}
                        >
                            {loading ? <><span className="spinner" /> Generating…</> : "Generate Reply ✨"}
                        </button>
                    </div>

                    {/* Output panel */}
                    <div className="panel">
                        <div className="panel-header">
                            <span className="panel-title">AI Reply</span>
                            {reply && (
                                <button
                                    className={`copy-reply-btn${copied ? " copied" : ""}`}
                                    onClick={handleCopy}
                                >
                                    {copied ? "✓ Copied" : "Copy"}
                                </button>
                            )}
                        </div>

                        {loading ? (
                            <div className="sr-loading">
                                <div className="sr-loading-dots">
                                    <span /><span /><span />
                                </div>
                                <p>Crafting your reply…</p>
                            </div>
                        ) : reply ? (
                            <div className="sr-reply-text">{reply}</div>
                        ) : (
                            <div className="coming-soon-placeholder">
                                <div className="coming-soon-icon">💬</div>
                                <div className="coming-soon-text">
                                    Your AI reply will appear here.<br />
                                    Paste a review and click Generate.
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
