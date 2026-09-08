import { z } from 'zod';

import { MedicalReviewStatus } from './enums';


// Children Filters

export const listChildrenFilterRequestSchema = z.object({
	is_active: z.boolean().nullable().optional(),
	review_status: z
		.array(z.enum(MedicalReviewStatus))
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
	review_status: z.enum(MedicalReviewStatus),

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
	review_status: z.enum(MedicalReviewStatus)
});

export type ChildTableResponse =
	z.infer<typeof childTableResponseSchema>;