import { z } from "zod";

// Aus State Enum
export const australianStateSchema = z.enum([
    "NSW",
    "VIC",
    "QLD",
    "WA",
    "SA",
    "TAS",
    "ACT",
    "NT",
]);

export type AustralianState =
    z.infer<typeof australianStateSchema>;

// Update Customer Profile

export const updateCustomerProfileRequestSchema = z.object({
    phone: z.string().nullable().optional(),
    address_line_1: z.string().nullable().optional(),
    address_line_2: z.string().nullable().optional(),
    suburb: z.string().nullable().optional(),
    state: australianStateSchema.nullable().optional(),
    postcode: z.string().nullable().optional(),
});


export type UpdateCustomerProfileRequest =
    z.infer<typeof updateCustomerProfileRequestSchema>;


// Customer Profile response

export const customerProfileResponseSchema = z.object({
    id: z.uuid(),
    user_id: z.uuid(),

    phone: z.string().nullable(),
    address_line_1: z.string().nullable(),
    address_line_2: z.string().nullable(),
    suburb: z.string().nullable(),
    state: australianStateSchema.nullable(),
    postcode: z.string().nullable(),
    
    updated_at: z.iso.datetime({ offset: true })
});

export type CustomerProfileResponse =
    z.infer<typeof customerProfileResponseSchema>;