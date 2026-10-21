import { createMedicalReviewsApi } from '$lib/api/public/adapters/medicalReviews';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch
}) => {
	depends('app:medical-reviews');

	// Both lists (waiting on staff, waiting on the family) in one call.
	const response = await createMedicalReviewsApi(fetch).list();
	const reviews = response.data ?? [];

	return {
		pending: reviews.filter((review) => review.review_status === 'pending'),
		requested: reviews.filter((review) => review.review_status === 'documentation_requested')
	};
};
