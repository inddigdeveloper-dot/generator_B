import { Link } from "react-router-dom";
import "../styles/Pricing.css";

const PLANS = [
    {
        name: "Free",
        price: "₹0",
        period: "/month",
        badge: null,
        highlight: false,
        features: [
            "5 AI reviews per month",
            "1 language (English)",
            "Basic QR code",
            "1 business profile",
            "Community support",
        ],
        cta: "Get Started",
        ctaTo: "/register",
    },
    {
        name: "Pro",
        price: "₹999",
        period: "/month",
        badge: "Most Popular",
        highlight: true,
        features: [
            "100 AI reviews per month",
            "All 3 languages",
            "Smart Reply AI",
            "Custom QR code",
            "Bill items AI",
            "Priority support",
        ],
        cta: "Start Pro",
        ctaTo: "/register",
    },
    {
        name: "Business",
        price: "₹2,499",
        period: "/month",
        badge: null,
        highlight: false,
        features: [
            "Unlimited AI reviews",
            "All 3 languages",
            "Smart Reply AI",
            "Custom branded QR",
            "Analytics dashboard",
            "Dedicated account manager",
            "API access",
        ],
        cta: "Contact Sales",
        ctaTo: "/register",
    },
];

export default function PricingPage() {
    return (
        <div className="inner-page">
            <div className="bg-orbs">
                <div className="orb orb-1" style={{ opacity: 0.07 }} />
                <div className="orb orb-3" style={{ opacity: 0.06 }} />
            </div>

            <div className="inner-page-body">
                <div className="page-header" style={{ textAlign: "center", marginBottom: 48 }}>
                    <div className="page-eyebrow">Pricing</div>
                    <h1 className="page-title">Simple, Transparent Pricing</h1>
                    <p className="page-sub">Choose the plan that fits your business. Upgrade or downgrade anytime.</p>
                </div>

                <div className="pricing-grid">
                    {PLANS.map(plan => (
                        <div
                            key={plan.name}
                            className={`pricing-card${plan.highlight ? " pricing-card--featured" : ""}`}
                        >
                            {plan.badge && (
                                <div className="pricing-badge">{plan.badge}</div>
                            )}
                            <div className="pricing-name">{plan.name}</div>
                            <div className="pricing-price">
                                {plan.price}
                                <span className="pricing-period">{plan.period}</span>
                            </div>

                            <ul className="pricing-features">
                                {plan.features.map(f => (
                                    <li key={f}>
                                        <span className="pricing-check">✓</span>
                                        {f}
                                    </li>
                                ))}
                            </ul>

                            <Link
                                to={plan.ctaTo}
                                className={`pricing-cta btn${plan.highlight ? " btn-primary" : " btn-ghost"}`}
                            >
                                {plan.cta}
                            </Link>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
