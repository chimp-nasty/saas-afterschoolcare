import { error } from '@sveltejs/kit';

import { isPlatformSite } from '$lib/platform/site';

import type { PageLoad } from './$types';

// The platform's contact page (docs/platform-site.md), on the platform's
// own site only. ?topic=own_business (Book a demo, and businesses' sites'
// "Interested in this software?") chooses the topic already.
export const load: PageLoad = async ({ url }) => {
	if (!isPlatformSite(url)) {
		error(404, 'Not Found');
	}

	const topic = url.searchParams.get('topic');

	return {
		topic: topic === 'own_business' || topic === 'build_software' ? topic : ''
	};
};
