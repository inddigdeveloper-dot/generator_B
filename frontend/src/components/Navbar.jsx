import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useTheme } from "../hooks/useTheme";
import InddigLogo from "./InddigLogo";
import "../styles/Navbar.css";

const NAV_LINKS = [
    { to: "/dashboard",     label: "Dashboard" },
    { to: "/smart-reply",   label: "Smart Reply" },
    { to: "/pricing",       label: "Pricing" },
    { to: "/order-history", label: "Order History" },
    { to: "/edit-business", label: "Edit Business" },
];

export default function Navbar() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    const { isDark, toggleTheme } = useTheme();

    const handleLogout = () => {
        logout();
        navigate("/login");
    };

    const initials = user?.name
        ? user.name.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase()
        : "U";

    return (
        <nav className="navbar">
            <Link to="/" className="navbar-brand">
                <InddigLogo size={200} />
            </Link>

            {user && (
                <div className="navbar-center">
                    {NAV_LINKS.map(link => (
                        <Link
                            key={link.to}
                            to={link.to}
                            className={`nav-link${location.pathname === link.to ? " nav-link-active" : ""}`}
                        >
                            {link.label}
                        </Link>
                    ))}
                </div>
            )}

            <div className="navbar-right">
                {/* Dark / Light toggle */}
                <button
                    className="theme-toggle"
                    onClick={toggleTheme}
                    title={isDark ? "Switch to light mode" : "Switch to dark mode"}
                    aria-label="Toggle theme"
                >
                    {isDark ? "☀️" : "🌙"}
                </button>

                {user ? (
                    <>
                        <div className="plan-badge">Plan · Free</div>
                        <div className="nav-avatar" title={user.name}>{initials}</div>
                        <button className="nav-btn-logout" onClick={handleLogout}>
                            Logout
                        </button>
                    </>
                ) : (
                    <>
                        <Link to="/login" className="nav-link">Sign in</Link>
                        <Link
                            to="/register"
                            className="btn btn-primary"
                            style={{ padding: "8px 20px", fontSize: "14px" }}
                        >
                            Get Started
                        </Link>
                    </>
                )}
            </div>
        </nav>
    );
}
