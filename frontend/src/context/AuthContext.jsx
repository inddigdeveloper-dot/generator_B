import { createContext, useState, useEffect } from "react";
import { getCurrentUser } from "../api/client";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem("token");
        if (token) {
            getCurrentUser()
                .then((userData) => setUser(userData))
                .catch(() => {
                    localStorage.removeItem("token");
                    localStorage.removeItem("refresh_token");
                })
                .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, []);

    const login = async (accessToken, refreshToken) => {
        localStorage.setItem("token", accessToken);
        localStorage.setItem("refresh_token", refreshToken);
        try {
            const userData = await getCurrentUser();
            setUser(userData);
        } catch {
            logout();
        }
    };

    const logout = () => {
        localStorage.removeItem("token");
        localStorage.removeItem("refresh_token");
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
}
