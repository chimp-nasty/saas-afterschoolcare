import { error } from '@sveltejs/kit';

import { createChildrenApi } from '$lib/api/public/adapters/children';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch,
	params
}) => {
	depends('app:child');

	const childrenApi = createChildrenApi(fetch);

	const childResponse = await childrenApi.getById(params.child_id);

	if (!childResponse.ok || !childResponse.data) {
		error(404, 'Child not found');
	}

	return {
		child: childResponse.data
	};
};
