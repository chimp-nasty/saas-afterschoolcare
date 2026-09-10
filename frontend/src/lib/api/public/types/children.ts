import { z } from 'zod';

import { medicalReviewStatusSchema } from './enums';


// Children Filters

export const listChildrenFilterRequestSchema = z.object({
	is_active: z.boolean().nullable().optional(),
	review_status: medicalReviewStatusSchema
		.nullable()
		.optional()
});

export type ListChildrenFilterRequest =
	z.infer<typeof listChildrenFilterRequestSchema>;


// Child Response

export const childResponseSchema = z.object({
	id: z.uuid(),
	location_id: z.uuid(),
	user_id: z.uuid(),

	first_name: z.string(),
	last_name: z.string(),
	dob: z.string(),

	medical_info: z.string().nullable(),
	allergy_info: z.string().nullable(),
	medication_info: z.string().nullable(),

	is_active: z.boolean(),
	review_status: medicalReviewStatusSchema,

	created_at: z.string(),
	updated_at: z.string()
});

export type ChildResponse =
	z.infer<typeof childResponseSchema>;


// Child Table Response

export const childTableResponseSchema = z.object({
	id: z.uuid(),
	location_id: z.uuid(),
	user_id: z.uuid(),

	first_name: z.string(),
	last_name: z.string(),
	dob: z.string(),

	is_active: z.boolean(),
	review_status: medicalReviewStatusSchema
});

export type ChildTableResponse =
	z.infer<typeof childTableResponseSchema>;


// Child Create Request

export const createChildRequestSchema = z.object({
	first_name: z.string(),
	last_name: z.string(),
	dob: z.date(),
	medical_info: z.string().nullable(),
	allergy_info: z.string().nullable(),
	medication_info: z.string().nullable()
});

export type CreateChildRequest =
	z.infer<typeof createChildRequestSchema>;