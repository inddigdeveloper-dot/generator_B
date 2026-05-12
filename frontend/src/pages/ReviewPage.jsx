import { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import "../styles/ReviewPage.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function ReviewPage() {
    const { username } = useParams();

    const [biz,         setBiz]         = useState(null);
    const [pageLoading, setPageLoading] = useState(true);
    const [pageError,   setPageError]   = useState("");

    const [rating,     setRating]     = useState(0);
    const [hovered,    setHovered]    = useState(0);
    const [experience, setExperience] = useState("");

    const [reviews,    setReviews]    = useState([]);
    const [activeIdx,  setActiveIdx]  = useState(0);   // visible card index
    const [selected,   setSelected]   = useState(null); // confirmed selection
    const [googleUrl,  setGoogleUrl]  = useState("");
    const [generating, setGenerating] = useState(false);
    const [genError,   setGenError]   = useState("");
    const [copied,     setCopied]     = useState(false);

    const scrollRef = useRef(null);

    useEffect(() => {
        fetch(`${API_URL}/r/${username}`)
            .then(r => r.json())
            .then(data => {
                if (data.detail) throw new Error(data.detail);
                setBiz(data);
            })
            .catch(e => setPageError(e.message || "Business not found"))
            .finally(() => setPageLoading(false));
    }, [username]);

    async function handleGenerate() {
        if (!rating) { setGenError("Please select a star rating."); return; }

        setGenerating(true);
        setGenError("");
        setReviews([]);
        setSelected(null);
        setActiveIdx(0);
        setGoogleUrl("");

        try {
            const res = await fetch(`${API_URL}/r/${username}/generate`, {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({ rating, experience: experience.trim() || null }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to generate reviews");
            setReviews(data.reviews);
            setGoogleUrl(data.google_review_url);
            // scroll to first card
            setTimeout(() => scrollToCard(0), 50);
        } catch (e) {
            setGenError(e.message);
        } finally {
            setGenerating(false);
        }
    }

    function scrollToCard(idx) {
        const container = scrollRef.current;
        if (!container) return;
        const card = container.children[idx];
        if (!card) return;
        card.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
        setActiveIdx(idx);
    }

    function handleScroll() {
        const container = scrollRef.current;
        if (!container) return;
        const scrollLeft = container.scrollLeft;
        const cardWidth  = container.offsetWidth;
        const idx        = Math.round(scrollLeft / cardWidth);
        setActiveIdx(Math.max(0, Math.min(idx, reviews.length - 1)));
    }

    function handleSelectCard(idx) {
        setSelected(idx);
        setCopied(false);
        scrollToCard(idx);
    }

    function handleCopy() {
        if (selected === null) return;
        navigator.clipboard.writeText(reviews[selected]);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    }

    function resetInput() {
        setRating(0);
        setExperience("");
        setReviews([]);
        setSelected(null);
        setActiveIdx(0);
        setGoogleUrl("");
        setGenError("");
    }

    const displayRating = hovered || rating;

    if (pageLoading) return (
        <div className="review-page">
            <div className="review-page-card">
                <div className="review-page-state">Loading...</div>
            </div>
        </div>
    );

    if (pageError) return (
        <div className="review-page">
            <div className="review-page-card">
                <div className="review-page-state error">{pageError}</div>
            </div>
        </div>
    );

    return (
        <div className="review-page">
            <div className="bg-orbs" aria-hidden="true">
                <div className="orb orb-1" />
                <div className="orb orb-2" />
                <div className="orb orb-3" />
            </div>

            <div className="review-page-card">
                <div className="review-page-header">
                    <div className="review-page-brand">Inddig<span>Media</span></div>
                    <div className="review-page-tagline">Turn experiences into expert reviews</div>
                </div>

                <div className="review-page-body">
                    {/* Business info */}
                    <div className="review-biz-box">
                        <div className="review-biz-name">{biz.business_name}</div>
                        <div className="review-biz-hint">Select stars for professional ideas</div>
                    </div>

                    {/* Star rating */}
                    <div className="review-stars" role="group" aria-label="Star rating">
                        {[1, 2, 3, 4, 5].map(n => (
                            <button
                                key={n}
                                className={`review-star-btn${displayRating >= n ? (hovered ? " preview" : " active") : ""}`}
                                onClick={() => { setRating(n); setReviews([]); setSelected(null); }}
                                onMouseEnter={() => setHovered(n)}
                                onMouseLeave={() => setHovered(0)}
                                aria-label={`${n} star${n > 1 ? "s" : ""}`}
                            >★</button>
                        ))}
                    </div>

                    {/* Experience input */}
                    <textarea
                        className="review-textarea"
                        placeholder="Describe your visit (optional) — the more you share, the more unique each review..."
                        value={experience}
                        onChange={e => { setExperience(e.target.value); setReviews([]); setSelected(null); }}
                        rows={3}
                    />

                    {genError && <div className="review-gen-error">{genError}</div>}

                    {/* Generate button */}
                    {!reviews.length && (
                        <button
                            className="review-btn-generate"
                            onClick={handleGenerate}
                            disabled={!rating || generating}
                        >
                            {generating
                                ? <><span className="spinner" /> Generating 5 reviews…</>
                                : "Generate Reviews"
                            }
                        </button>
                    )}

                    {/* ── Carousel ─────────────────────────────────────────── */}
                    {reviews.length > 0 && (
                        <>
                            <div className="review-carousel-header">
                                <span className="review-carousel-label">
                                    Swipe to browse · tap to select
                                </span>
                                <span className="review-carousel-counter">
                                    {activeIdx + 1} / {reviews.length}
                                </span>
                            </div>

                            {/* Scrollable track */}
                            <div
                                className="review-carousel"
                                ref={scrollRef}
                                onScroll={handleScroll}
                            >
                                {reviews.map((text, idx) => (
                                    <div
                                        key={idx}
                                        className={`review-card ${selected === idx ? "review-card--selected" : ""}`}
                                        onClick={() => handleSelectCard(idx)}
                                    >
                                        <div className="review-card-inner">
                                            <div className="review-card-top">
                                                <span className="review-card-num">{idx + 1}</span>
                                                {selected === idx && (
                                                    <span className="review-card-badge">Selected ✓</span>
                                                )}
                                            </div>
                                            <p className="review-card-text">{text}</p>
                                            {selected !== idx && (
                                                <span className="review-card-tap-hint">Tap to select</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Dot indicators */}
                            <div className="review-dots">
                                {reviews.map((_, idx) => (
                                    <button
                                        key={idx}
                                        className={`review-dot ${idx === activeIdx ? "review-dot--active" : ""} ${idx === selected ? "review-dot--selected" : ""}`}
                                        onClick={() => scrollToCard(idx)}
                                        aria-label={`Review ${idx + 1}`}
                                    />
                                ))}
                            </div>

                            {/* Action buttons */}
                            <div className="review-actions">
                                {selected !== null ? (
                                    <>
                                        <button
                                            className={`review-btn-copy ${copied ? "copied" : ""}`}
                                            onClick={handleCopy}
                                        >
                                            {copied ? "✓ Copied!" : "📋 Copy Selected Review"}
                                        </button>

                                        <a
                                            className="review-btn-open"
                                            href={googleUrl}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                        >
                                            ⭐ Open Google Review
                                        </a>
                                    </>
                                ) : (
                                    <p className="review-select-hint">← Swipe and tap a review to select it</p>
                                )}

                                <button
                                    className="review-btn-regenerate"
                                    onClick={handleGenerate}
                                    disabled={generating}
                                >
                                    {generating ? <><span className="spinner" /> Regenerating…</> : "↺ Generate New Set"}
                                </button>

                                <button className="review-btn-reset" onClick={resetInput}>
                                    Start Over
                                </button>
                            </div>
                        </>
                    )}
                </div>

                <div className="review-page-footer">
                    Professional Review Generation by Inddig Media
                </div>
            </div>
        </div>
    );
}
