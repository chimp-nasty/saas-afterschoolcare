import { z } from "zod";

export const actionResponseSchema = z.object({
    id: z.uuid(),
    user_id: z.uuid(),
    child_id: z.uuid().nullable(),

    target: z.string(),
    title: z.string(),
    message: z.string(),

    created_by_user_id: z.uuid(),
    created_at: z.date(),
    cited_at: z.date().nullable()
});

export type ActionResponse = 
    z.infer<typeof actionResponseSchema>;