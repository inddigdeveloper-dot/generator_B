import { GoogleLogin } from "@react-oauth/google";
import { useNavigate } from "react-router-dom";
import { googleLogin } from "../api/client";
import { useAuth } from "../hooks/useAuth";

export default function GoogleLoginButton() {
    const navigate = useNavigate();
    const { login } = useAuth();

    const handleSuccess = async (credentialResponse) => {
        try {
            const result = await googleLogin({ token: credentialResponse.credential });
            await login(result.access_token, result.refresh_token);
            navigate("/dashboard");
        } catch (err) {
            console.error("Google login failed:", err);
        }
    };

    return (
        <div className="google-btn-wrapper">
            <GoogleLogin
                onSuccess={handleSuccess}
                onError={() => console.error("Google login error")}
                theme="filled_black"
                size="large"
                shape="rectangular"
                text="signin_with"
            />
        </div>
    );
}
