import { error } from '@sveltejs/kit';

import { createChildDocumentsApi } from '$lib/api/public/adapters/childDocuments';
import { createMedicalReviewsApi } from '$lib/api/public/adapters/medicalReviews';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch,
	params
}) => {
	depends('app:medical-review');

	const [reviewResponse, documentsResponse] = await Promise.all([
		createMedicalReviewsApi(fetch).get(params.child_id),
		createChildDocumentsApi(fetch).list(params.child_id)
	]);

	if (!reviewResponse.ok || !reviewResponse.data) {
		error(404, 'Child not found');
	}

	return {
		review: reviewResponse.data,
		documents: documentsResponse.data ?? []
	};
};
