import { z } from 'zod';

import { currencyCodeSchema } from './enums';

export const updateLocationServiceRequestSchema = z.object({
	amount_cents: z
		.number()
		.int('Price must be a whole number of cents')
		.positive('Price must be greater than zero'),

	currency: currencyCodeSchema
});

export type UpdateLocationServiceRequest =
	z.infer<typeof updateLocationServiceRequestSchema>;


export const locationServiceSelectionResponseSchema = z.object({
	id: z.uuid(),
	service_type_id: z.int(),
	service_name: z.string(),
	current_price_cents: z.int(),
	currency: currencyCodeSchema
});

export type LocationServiceSelectionResponse =
	z.infer<typeof locationServiceSelectionResponseSchema>;