import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const api = axios.create({
    baseURL: BASE_URL,
    timeout: 10000,
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem("token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token)));
    failedQueue = [];
};

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const original = error.config;
        if (error.response?.status === 401 && !original._retry) {
            const refreshToken = localStorage.getItem("refresh_token");
            if (!refreshToken) {
                localStorage.removeItem("token");
                window.location.href = "/login";
                return Promise.reject(error);
            }

            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                })
                    .then((token) => {
                        original.headers.Authorization = `Bearer ${token}`;
                        return api(original);
                    })
                    .catch((err) => Promise.reject(err));
            }

            original._retry = true;
            isRefreshing = true;

            try {
                const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
                    refresh_token: refreshToken,
                });
                localStorage.setItem("token", data.access_token);
                localStorage.setItem("refresh_token", data.refresh_token);
                api.defaults.headers.common.Authorization = `Bearer ${data.access_token}`;
                processQueue(null, data.access_token);
                original.headers.Authorization = `Bearer ${data.access_token}`;
                return api(original);
            } catch (refreshError) {
                processQueue(refreshError, null);
                localStorage.removeItem("token");
                localStorage.removeItem("refresh_token");
                window.location.href = "/login";
                return Promise.reject(refreshError);
            } finally {
                isRefreshing = false;
            }
        }
        return Promise.reject(error);
    }
);

export const registerUser = async (userData) => {
    try {
        const { data } = await api.post("/auth/register", userData);
        return data;
    } catch (error) {
        throw error.response?.data?.detail || "Registration failed";
    }
};

export const loginUser = async (userData) => {
    try {
        const { data } = await api.post("/auth/login", userData);
        return data;
    } catch (error) {
        throw error.response?.data?.detail || "Login failed";
    }
};

export const googleLogin = async (userData) => {
    try {
        const { data } = await api.post("/auth/google", userData);
        return data;
    } catch (error) {
        throw error.response?.data?.detail || "Google login failed";
    }
};

export const getCurrentUser = async () => {
    try {
        const { data } = await api.get("/auth/me");
        return data;
    } catch (error) {
        throw error.response?.data?.detail || "Failed to fetch user profile";
    }
};

export const generateReview = async (reviewData) => {
    try {
        const { data } = await api.post("/reviews/generate", reviewData);
        return data;
    } catch (error) {
        throw error.response?.data?.detail || "Failed to generate review";
    }
};

export const getReviewHistory = async () => {
    try {
        const { data } = await api.get("/reviews/history");
        return data;
    } catch (error) {
        throw error.response?.data?.detail || "Failed to fetch review history";
    }
};

export const getQRCode = async () => {
    try {
        const { data } = await api.post("/reviews/qr");
        return data;
    } catch (error) {
        throw error.response?.data?.detail || "Failed to get QR code";
    }
};

export const updateUserProfile = async (profileData) => {
    try {
        const { data } = await api.patch("/auth/me", profileData);
        return data;
    } catch (error) {
        throw error.response?.data?.detail || "Failed to update profile";
    }
};

export default api;
