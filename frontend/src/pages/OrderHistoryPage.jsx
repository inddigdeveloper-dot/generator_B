import { useState, useEffect } from "react";
import { getReviewHistory } from "../api/client";
import "../styles/OrderHistory.css";

const STAR = "⭐";
const PAGE_SIZE = 20;

export default function OrderHistoryPage() {
    const [reviews,  setReviews]  = useState([]);
    const [total,    setTotal]    = useState(0);
    const [page,     setPage]     = useState(0);
    const [loading,  setLoading]  = useState(true);
    const [error,    setError]    = useState("");

    useEffect(() => {
        setLoading(true);
        setError("");
        getReviewHistory({ skip: page * PAGE_SIZE, limit: PAGE_SIZE })
            .then(data => {
                setReviews(data.reviews);
                setTotal(data.total);
            })
            .catch(err => setError(typeof err === "string" ? err : "Failed to load review history."))
            .finally(() => setLoading(false));
    }, [page]);

    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    return (
        <div className="inner-page">
            <div className="bg-orbs">
                <div className="orb orb-1" style={{ opacity: 0.07 }} />
            </div>

            <div className="inner-page-body">
                <div className="page-header">
                    <div className="page-eyebrow">Review History</div>
                    <h1 className="page-title">Generated Reviews</h1>
                    <p className="page-sub">All AI-generated reviews for your business ({total} total).</p>
                </div>

                <div className="panel oh-panel" style={{ animationDelay: "0.1s" }}>
                    {loading ? (
                        <div className="coming-soon-placeholder">
                            <div className="coming-soon-text">Loading…</div>
                        </div>
                    ) : error ? (
                        <div className="coming-soon-placeholder">
                            <div className="coming-soon-icon">⚠️</div>
                            <div className="coming-soon-text">{error}</div>
                        </div>
                    ) : reviews.length > 0 ? (
                        <>
                            <table className="oh-table">
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>Customer</th>
                                        <th>Rating</th>
                                        <th>Review</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {reviews.map((r, i) => (
                                        <tr key={r.id}>
                                            <td className="oh-id">{page * PAGE_SIZE + i + 1}</td>
                                            <td>{r.customer_name}</td>
                                            <td style={{ whiteSpace: "nowrap" }}>
                                                {STAR.repeat(r.rating)}
                                            </td>
                                            <td style={{ maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                                {r.review_text}
                                            </td>
                                            <td style={{ whiteSpace: "nowrap" }}>
                                                {new Date(r.created_at).toLocaleDateString()}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>

                            {totalPages > 1 && (
                                <div style={{ display: "flex", gap: "0.5rem", justifyContent: "center", padding: "1rem 0" }}>
                                    <button
                                        className="btn btn-ghost"
                                        onClick={() => setPage(p => Math.max(0, p - 1))}
                                        disabled={page === 0}
                                    >
                                        ← Prev
                                    </button>
                                    <span style={{ alignSelf: "center", opacity: 0.7 }}>
                                        {page + 1} / {totalPages}
                                    </span>
                                    <button
                                        className="btn btn-ghost"
                                        onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                                        disabled={page >= totalPages - 1}
                                    >
                                        Next →
                                    </button>
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="coming-soon-placeholder">
                            <div className="coming-soon-icon">🧾</div>
                            <div className="coming-soon-text">
                                No reviews generated yet.<br />
                                Go to the Dashboard and generate your first review.
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
