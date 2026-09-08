import z from "zod";

export const resetPasswordFormSchema = z
    .object({
        password: z
            .string()
            .min(8, 'Password must be at least 8 characters')
            .max(128, 'Password must be no more than 128 characters'),

        confirmPassword: z.string()
    })
    .refine(
        (body) => body.password === body.confirmPassword,
        {
            message: 'Passwords do not match',
            path: ['confirmPassword']
        }
    );

export type ResetPasswordForm =
    z.infer<typeof resetPasswordFormSchema>;