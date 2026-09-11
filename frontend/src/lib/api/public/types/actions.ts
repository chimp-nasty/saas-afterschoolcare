import { z } from "zod";
import { dateTimeSchema } from '$lib/types/dates';

// Action Response

export const actionResponseSchema = z.object({
    id: z.uuid(),
    user_id: z.uuid(),
    child_id: z.uuid().nullable(),

    target: z.string(),
    title: z.string(),
    message: z.string(),

    created_by_user_id: z.uuid(),
    created_at: dateTimeSchema,
    cited_at: dateTimeSchema.nullable()
});

export type ActionResponse = 
    z.infer<typeof actionResponseSchema>;


// Action Filter

export const actionFiltersSchema = z.object({
    cited: z.boolean().optional(),
    user_id: z.uuid().optional(),
    target: z.string().optional(),
});

export type ActionFilter =
    z.infer<typeof actionFiltersSchema>;