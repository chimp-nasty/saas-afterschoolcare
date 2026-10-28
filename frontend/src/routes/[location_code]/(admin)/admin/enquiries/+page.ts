import { createEnquiriesApi } from '$lib/api/public/adapters/enquiries';

import type { PageLoad } from './$types';

// Every enquiry (the newest 200) in one call; the tabs split them.
export const load: PageLoad = async ({ depends, fetch }) => {
	depends('app:enquiries');

	const response = await createEnquiriesApi(fetch).list('all');
	const enquiries = response.data ?? [];

	return {
		open: enquiries.filter((enquiry) => enquiry.status !== 'closed'),
		closed: enquiries.filter((enquiry) => enquiry.status === 'closed'),
		all: enquiries
	};
};
