// Login
export type LoginRequest = {
    email: string;
    password: string;
}

// Forgot Password
export type ForgotPasswordRequest = {
    email: string;
}

// Reset Password
export type ResetPasswordRequest = {
    token: string;
    password: string;
}

// Session
export type SessionResponse = {
    user_id: string;
    location_id: string;
}
