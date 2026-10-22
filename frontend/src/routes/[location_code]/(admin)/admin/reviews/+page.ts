import { createMedicalReviewsApi } from '$lib/api/public/adapters/medicalReviews';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch,
	url
}) => {
	depends('app:medical-reviews');

	const api = createMedicalReviewsApi(fetch);
	// A child's or parent's name, searching every list (2 letters or more).
	const q = url.searchParams.get('q')?.trim() ?? '';
	const search = q.length >= 2 ? { q } : {};

	// The two waiting lists (on staff, on the family) in one call, and the
	// approved children (newest decision first).
	const [waiting, approved] = await Promise.all([
		api.list(search),
		api.list({ ...search, review_status: ['approved'] })
	]);
	const reviews = waiting.data ?? [];

	return {
		q,
		pending: reviews.filter((review) => review.review_status === 'pending'),
		requested: reviews.filter((review) => review.review_status === 'documentation_requested'),
		approved: approved.data ?? []
	};
};
