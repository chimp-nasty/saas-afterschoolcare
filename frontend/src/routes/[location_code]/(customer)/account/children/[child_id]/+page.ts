import { error } from '@sveltejs/kit';

import { createChildrenApi } from '$lib/api/public/adapters/children';
import { createChildDocumentsApi } from '$lib/api/public/adapters/childDocuments';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch,
	params
}) => {
	// The child and their documents refresh together: a document change
	// also changes the child's review status.
	depends('app:child');

	const childrenApi = createChildrenApi(fetch);
	const documentsApi = createChildDocumentsApi(fetch);

	const [childResponse, documentsResponse] = await Promise.all([
		childrenApi.getById(params.child_id),
		documentsApi.list(params.child_id)
	]);

	if (!childResponse.ok || !childResponse.data) {
		error(404, 'Child not found');
	}

	return {
		child: childResponse.data,
		documents: documentsResponse.data ?? []
	};
};
