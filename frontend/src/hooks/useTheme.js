import { useState, useEffect } from "react";

export function useTheme() {
    const [theme, setTheme] = useState(() => {
        try {
            const saved = localStorage.getItem("inddig-theme");
            if (saved) return saved;
            return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
        } catch {
            return "light";
        }
    });

    useEffect(() => {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("inddig-theme", theme);
    }, [theme]);

    const toggleTheme = () => setTheme(t => (t === "light" ? "dark" : "light"));

    return { theme, toggleTheme, isDark: theme === "dark" };
}
