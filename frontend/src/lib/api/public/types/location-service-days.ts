import { z } from 'zod';

import { dateSchema } from '$lib/types/dates';

// Location Service Day Filters

export const listLocationServiceDaysFilterRequestSchema = z.object({
	date_from: z.iso.date().nullable().optional(),
	date_to: z.iso.date().nullable().optional(),
	is_open: z.boolean().nullable().optional()
});

export type ListLocationServiceDaysFilterRequest =
	z.infer<typeof listLocationServiceDaysFilterRequestSchema>;


// Location Service Day Table Response

export const locationServiceDayTableResponseSchema = z.object({
	id: z.uuid(),
	location_service_id: z.uuid(),
	service_type_id: z.number(),

	service_name: z.string(),
	service_date: dateSchema,

	is_open: z.boolean(),
	capacity: z.number()
});

export type LocationServiceDayTableResponse =
	z.infer<typeof locationServiceDayTableResponseSchema>;