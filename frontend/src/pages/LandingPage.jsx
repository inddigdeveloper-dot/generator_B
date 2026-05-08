import { Link } from "react-router-dom";
import InddigLogo from "../components/InddigLogo";
import "../styles/LandingPage.css";

const features = [
    {
        icon: "⚡",
        iconClass: "icon-blue",
        title: "AI-Powered Reviews",
        desc: "Generate authentic, human-sounding Google reviews tailored to your business in seconds.",
    },
    {
        icon: "🎯",
        iconClass: "icon-cyan",
        title: "SEO Optimised",
        desc: "Reviews are crafted with your keywords to boost your local search ranking organically.",
    },
    {
        icon: "🔒",
        iconClass: "icon-indigo",
        title: "Secure & Private",
        desc: "Your business data is encrypted and never shared. Full GDPR compliance built in.",
    },
];

const stats = [
    { number: "10K+", label: "Reviews Generated" },
    { number: "98%",  label: "Satisfaction Rate" },
    { number: "2.4×", label: "Avg Rating Boost" },
];

export default function LandingPage() {
    return (
        <div className="landing">
            <div className="bg-orbs">
                <div className="orb orb-1" />
                <div className="orb orb-2" />
                <div className="orb orb-3" />
            </div>

            <div className="landing-content">
                <div className="landing-brand-row">
                    {/* <InddigLogo size={150} /> */}
                    <span className="landing-brand-name">inddig<span>media</span></span>
                </div>

                <div className="landing-badge">
                    <span className="badge-dot" />
                    AI-powered review generation
                </div>

                <h1 className="landing-title">
                    Grow Your Business<br />
                    with <span className="highlight">Smart Reviews</span>
                </h1>

                <p className="landing-subtitle">
                    Generate authentic, SEO-optimised Google Business reviews that
                    build trust, boost visibility, and drive more customers to your door.
                </p>

                <div className="landing-cta">
                    <Link to="/register" className="btn btn-primary">
                        Start for Free →
                    </Link>
                    <Link to="/login" className="btn btn-ghost">
                        Sign In
                    </Link>
                </div>
            </div>

            <div className="landing-stats">
                {stats.map(s => (
                    <div className="stat-item" key={s.label}>
                        <div className="stat-number gradient-text">{s.number}</div>
                        <div className="stat-label">{s.label}</div>
                    </div>
                ))}
            </div>

            <div className="landing-features">
                {features.map(f => (
                    <div className="feature-card" key={f.title}>
                        <div className={`feature-icon ${f.iconClass}`}>{f.icon}</div>
                        <div className="feature-title">{f.title}</div>
                        <div className="feature-desc">{f.desc}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
