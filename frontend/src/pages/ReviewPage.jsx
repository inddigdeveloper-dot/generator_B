import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import "../styles/ReviewPage.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function ReviewPage() {
    const { username } = useParams();

    const [biz, setBiz] = useState(null);
    const [pageLoading, setPageLoading] = useState(true);
    const [pageError, setPageError] = useState("");

    const [rating, setRating] = useState(0);
    const [hovered, setHovered] = useState(0);
    const [experience, setExperience] = useState("");

    const [reviewText, setReviewText] = useState("");
    const [googleUrl, setGoogleUrl] = useState("");
    const [generating, setGenerating] = useState(false);
    const [genError, setGenError] = useState("");
    const [copied, setCopied] = useState(false);

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
        if (!rating) {
            setGenError("Please select a star rating.");
            return;
        }

        setGenerating(true);
        setGenError("");
        setReviewText("");
        setGoogleUrl("");
        
        try {
            const res = await fetch(`${API_URL}/r/${username}/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    rating: rating, 
                    experience: experience.trim() || null 
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to generate review");
            setReviewText(data.review_text);
            setGoogleUrl(data.google_review_url);
        } catch (e) {
            setGenError(e.message);
        } finally {
            setGenerating(false);
        }
    }

    function handleCopy() {
        navigator.clipboard.writeText(reviewText);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    }

    // Active star display = hovered if hovering, else selected
    const displayRating = hovered || rating;

    if (pageLoading) {
        return (
            <div className="review-page">
                <div className="review-page-card">
                    <div className="review-page-state">Loading...</div>
                </div>
            </div>
        );
    }

    if (pageError) {
        return (
            <div className="review-page">
                <div className="review-page-card">
                    <div className="review-page-state error">{pageError}</div>
                </div>
            </div>
        );
    }

    return (
        <div className="review-page">
            <div className="bg-orbs" aria-hidden="true">
                <div className="orb orb-1" />
                <div className="orb orb-2" />
                <div className="orb orb-3" />
            </div>

            <div className="review-page-card">
                <div className="review-page-header">
                    <div className="review-page-brand">
                        Inddig<span>Media</span>
                    </div>
                    <div className="review-page-tagline">
                        Turn experiences into expert reviews
                    </div>
                </div>

                <div className="review-page-body">
                    {/* Business info */}
                    <div className="review-biz-box">
                        <div className="review-biz-name">{biz.business_name}</div>
                        {/* {biz.business_desc && (
                            <div className="review-biz-desc">{biz.business_desc}</div>
                        )} */}
                        <div className="review-biz-hint">Select stars for professional ideas</div>
                    </div>

                    {/* Star rating */}
                    <div className="review-stars" role="group" aria-label="Star rating">
                        {[1, 2, 3, 4, 5].map(n => (
                            <button
                                key={n}
                                className={`review-star-btn${
                                    displayRating >= n
                                        ? hovered ? " preview" : " active"
                                        : ""
                                }`}
                                onClick={() => { setRating(n); setReviewText(""); setGoogleUrl(""); }}
                                onMouseEnter={() => setHovered(n)}
                                onMouseLeave={() => setHovered(0)}
                                aria-label={`${n} star${n > 1 ? "s" : ""}`}
                            >
                                ★
                            </button>
                        ))}
                    </div>

                    {/* Experience input — always visible so user can edit and regenerate */}
                    <textarea
                        className="review-textarea"
                        placeholder="Describe your visit (optional) — the more you share, the better the review..."
                        value={experience}
                        onChange={e => { setExperience(e.target.value); setReviewText(""); setGoogleUrl(""); }}
                        rows={4}
                    />

                    {/* Generated review */}
                    {reviewText && (
                        <textarea
                            className="review-textarea generated"
                            value={reviewText}
                            onChange={e => setReviewText(e.target.value)}
                            rows={5}
                        />
                    )}

                    {genError && (
                        <div className="review-gen-error">{genError}</div>
                    )}

                    <div className="review-actions">
                        <button
                            className="review-btn-generate"
                            onClick={handleGenerate}
                            disabled={!rating || generating}
                        >
                            {generating
                                ? <><span className="spinner" /> Generating...</>
                                : reviewText ? "↺ Regenerate Review" : "Generate Review"
                            }
                        </button>

                        {reviewText && (
                            <>
                                <button
                                    className={`review-btn-copy${copied ? " copied" : ""}`}
                                    onClick={handleCopy}
                                >
                                    {copied ? "✓ Copied to clipboard!" : "📋 Copy Review Text"}
                                </button>

                                <a
                                    className="review-btn-open"
                                    href={googleUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    ⭐ Ready to Review
                                </a>
                            </>
                        )}
                    </div>
                </div>

                <div className="review-page-footer">
                    Professional Review Generation by Inddig Media
                </div>
            </div>
        </div>
    );
}
