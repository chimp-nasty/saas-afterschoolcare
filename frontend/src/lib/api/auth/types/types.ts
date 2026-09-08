import z from "zod";


// Login
export const loginRequestSchema = z.object({
    email: z.email('Enter a valid email address'),
    password: z.string().min(1, 'Password is required')
});

export type LoginRequest = z.infer<typeof loginRequestSchema>;


// Forgot Password
export const forgotPasswordRequestSchema = z.object({
    email: z.email('Enter a valid email address')
});

export type ForgotPasswordRequest = z.infer<typeof forgotPasswordRequestSchema>;


// Reset Password
export const resetPasswordRequestSchema = z.object({
    token: z.string(),
    password: z
        .string()
        .min(8, 'Password must be at least 8 characters')
        .max(128, 'Password must be no more than 128 characters')
});

export type ResetPasswordRequest = z.infer<typeof resetPasswordRequestSchema>;

    
// Session
export const sessionResponseSchema = z.object({
    user_id: z.uuid(),
    location_id: z.uuid(),
    email: z.email(),
    first_name: z.string(),
    roles: z.array(z.string())
});

export type SessionResponse = z.infer<typeof sessionResponseSchema>;


// Registration
export const registrationRequestSchema = z.object({
    email: z.email('Enter a valid email address'),

    password: z
        .string()
        .min(8, 'Password must be at least 8 characters')
        .max(128, 'Password must be no more than 128 characters'),

    first_name: z
        .string()
        .min(1, 'First name is required')
        .max(255, 'First name must be no more than 255 characters'),

    last_name: z
        .string()
        .min(1, 'Last name is required')
        .max(255, 'Last name must be no more than 255 characters'),

    terms_accepted: z.literal(
        true,
        'You must accept the terms and conditions'
    )
});

export type RegistrationRequest =
    z.infer<typeof registrationRequestSchema>;