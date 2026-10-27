// Uploading files for the public site: the business's logo and icon (Your
// site), its policies, and the photos (the business's, a centre's and a
// program's, inline on the pages). The browser sends the file straight to
// storage, then the server checks it (it reads the file itself, whatever
// the browser claimed) and uses it.
import { toast } from 'svelte-sonner';

import { uploadToStorage } from '$lib/api/storage';
import type { createBusinessApi } from '$lib/api/tenancy/adapters/business';
import type { SiteFileKind } from '$lib/api/tenancy/adapters/location-branding';
import type { SiteUploadResponse, StartSiteUploadRequest } from '$lib/api/schema';
import type { ApiResponse } from '$lib/api/wrapper';

type ContentType = StartSiteUploadRequest['content_type'];

// What a photo may be (re-saved as a JPEG by the server).
export const PHOTO_ACCEPT: ContentType[] = ['image/png', 'image/jpeg', 'image/webp'];

// The types each of the business's files may be.
export const SITE_FILE_ACCEPT: Record<SiteFileKind, ContentType[]> = {
	logo: PHOTO_ACCEPT,
	icon: ['image/png'],
	hero_photo: PHOTO_ACCEPT,
	about_photo: PHOTO_ACCEPT,
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
export async function uploadFile<T extends ContentType>(
	file: File,
	{
		accept,
		wrongType,
		start,
		confirm
	}: {
		accept: T[];
		wrongType: string;
		start: (contentType: T) => Promise<ApiResponse<SiteUploadResponse>>;
		confirm: (key: string) => Promise<ApiResponse<unknown>>;
	}
): Promise<boolean> {
	const contentType = accept.find((type) => type === file.type);

	if (!contentType) {
		toast.error(wrongType);
		return false;
	}

	const started = await start(contentType);

	if (!started.ok || !started.data) return false;

	if (!(await uploadToStorage(started.data, file))) {
		toast.error("The file couldn't be uploaded. Check it's small enough and try again.");
		return false;
	}

	return (await confirm(started.data.key)).ok;
}

// One of the business's own files.
export function uploadSiteFile(
	businessApi: ReturnType<typeof createBusinessApi>,
	kind: SiteFileKind,
	file: File
): Promise<boolean> {
	return uploadFile(file, {
		accept: SITE_FILE_ACCEPT[kind],
		wrongType: WRONG_TYPE[kind],
		start: (contentType) => businessApi.startUpload({ kind, content_type: contentType }),
		confirm: (key) => businessApi.confirmUpload({ kind, key })
	});
}

// A centre's or a program's photo, through its own start and confirm calls.
export function uploadPhoto(
	file: File,
	start: (
		contentType: 'image/png' | 'image/jpeg' | 'image/webp'
	) => Promise<ApiResponse<SiteUploadResponse>>,
	confirm: (key: string) => Promise<ApiResponse<unknown>>
): Promise<boolean> {
	return uploadFile(file, {
		accept: ['image/png', 'image/jpeg', 'image/webp'],
		wrongType: 'Choose a PNG, JPEG or WebP photo.',
		start,
		confirm
	});
}
