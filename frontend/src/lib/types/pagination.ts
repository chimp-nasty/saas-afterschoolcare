import { z } from "zod";

export const paginationSchema = z.object({
    page: z.int().optional(),
    limit: z.int().optional(),
})

export type Pagination =
    z.infer<typeof paginationSchema>;

export type PaginationLoadMode =
    | 'replace'
    | 'append';