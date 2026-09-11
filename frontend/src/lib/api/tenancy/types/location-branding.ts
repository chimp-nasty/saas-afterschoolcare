import { z } from 'zod';

export const publicLocationResponseSchema = z.object({
    tenant_name: z.string(),
    tenant_code: z.string(),

    location_code: z.string(),
    location_name: z.string(),

    display_name: z.string().nullable(),
    logo_key: z.string().nullable(),

    primary_color: z.string().nullable(),
    secondary_color: z.string().nullable(),
    font_family: z.string().nullable()
});

export type PublicLocationResponse =
    z.infer<typeof publicLocationResponseSchema>;