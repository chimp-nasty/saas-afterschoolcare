import z from "zod";

import type { FormErrors } from "$lib/types/forms";

export function createFormState<T extends object>(
	initialState: T
): T {
	return structuredClone(initialState);
}

export function validateForm<T>(
    schema: z.ZodType<T>,
    body: T
): {
    valid: boolean;
    errors: FormErrors<T>;
} {
    const result = schema.safeParse(body);

    if (result.success) {
        return {
            valid: true,
            errors: {}
        };
    }

    const errors: FormErrors<T> = {};

    for (const issue of result.error.issues) {
        const field = issue.path[0] as keyof T;

        if (field && !errors[field]) {
            errors[field] = issue.message;
        }
    }

    return {
        valid: false,
        errors
    };
}