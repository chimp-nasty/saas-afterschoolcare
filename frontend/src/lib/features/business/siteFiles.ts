// Uploading the business's site files: the logo and icon (Your site), the
// photos (inline on the pages) and the policies. The browser sends the
// file straight to storage, then the server checks it (it reads the file
// itself, whatever the browser claimed) and uses it.
import { toast } from 'svelte-sonner';

import { uploadToStorage } from '$lib/api/storage';
import type { createBusinessApi } from '$lib/api/tenancy/adapters/business';
import type { SiteFileKind } from '$lib/api/tenancy/adapters/location-branding';
import type { StartSiteUploadRequest } from '$lib/api/schema';

const IMAGES: StartSiteUploadRequest['content_type'][] = ['image/png', 'image/jpeg', 'image/webp'];

// The types each file may be.
export const SITE_FILE_ACCEPT: Record<SiteFileKind, StartSiteUploadRequest['content_type'][]> = {
	logo: IMAGES,
	icon: ['image/png'],
	hero_photo: IMAGES,
	about_photo: IMAGES,
	privacy: ['application/pdf'],
	terms: ['application/pdf']
};

const WRONG_TYPE: Record<SiteFileKind, string> = {
	logo: 'Choose a PNG, JPEG or WebP image.',
	icon: 'Choose a square PNG image.',
	hero_photo: 'Choose a PNG, JPEG or WebP photo.',
	about_photo: 'Choose a PNG, JPEG or WebP photo.',
	privacy: 'Choose a PDF.',
	terms: 'Choose a PDF.'
};

// Start the upload, send the file, then have the server check and use it.
// True once it's in use; any problem is toasted. The caller refreshes.
export async function uploadSiteFile(
	businessApi: ReturnType<typeof createBusinessApi>,
	kind: SiteFileKind,
	file: File
): Promise<boolean> {
	const contentType = SITE_FILE_ACCEPT[kind].find((type) => type === file.type);

	if (!contentType) {
		toast.error(WRONG_TYPE[kind]);
		return false;
	}

	const started = await businessApi.startUpload({ kind, content_type: contentType });

	if (!started.ok || !started.data) return false;

	if (!(await uploadToStorage(started.data, file))) {
		toast.error("The file couldn't be uploaded. Check it's small enough and try again.");
		return false;
	}

	const confirmed = await businessApi.confirmUpload({ kind, key: started.data.key });

	return confirmed.ok;
}
