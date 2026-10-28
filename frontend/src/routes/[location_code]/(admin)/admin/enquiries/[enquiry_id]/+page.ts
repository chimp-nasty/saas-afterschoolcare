import { error } from '@sveltejs/kit';

import { createEnquiriesApi } from '$lib/api/public/adapters/enquiries';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends, fetch, params }) => {
	depends('app:enquiry');

	const response = await createEnquiriesApi(fetch).get(params.enquiry_id);

	if (!response.ok || !response.data) {
		error(404, 'Enquiry not found');
	}

	return { enquiry: response.data };
};
