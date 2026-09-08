import z from "zod";

export const registrationFormSchema = z
	.object({
		email: z.email('Enter a valid email address'),

		password: z
			.string()
			.min(8, 'Password must be at least 8 characters')
			.max(128, 'Password must be no more than 128 characters'),

		confirmPassword: z.string(),

		first_name: z
			.string()
			.min(1, 'First name is required')
			.max(255),

		last_name: z
			.string()
			.min(1, 'Last name is required')
			.max(255),

		terms_accepted: z.boolean()
	})
	.refine(
		(body) => body.password === body.confirmPassword,
		{
			message: 'Passwords do not match',
			path: ['confirmPassword']
		}
	)
	.refine(
		(body) => body.terms_accepted,
		{
			message: 'You must accept terms to continue',
			path: ['terms_accepted']
		}
	);

export type RegistrationForm =
	z.infer<typeof registrationFormSchema>;