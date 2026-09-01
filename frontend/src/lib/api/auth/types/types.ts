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
    email: string | null;
    first_name: string | null;
    roles: string[];
}


// Registration
export type RegistrationRequest = {
    email: string;
    password: string;

    first_name: string;
    last_name: string;

    terms_accepted: boolean;
}