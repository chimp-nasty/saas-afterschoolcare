import type { SignedUploadResponse } from '$lib/api/schema';


/**
 * Step 2 of a document upload: send the file straight to storage (GCS or
 * S3) with the signed fields the API returned. No cookies go with it; the
 * signature is the permission, and storage enforces its limits (type,
 * size). XHR rather than fetch so large files can report progress.
 *
 * Resolves true once storage has the file.
 */
export function uploadToStorage(
	upload: Pick<SignedUploadResponse, 'url' | 'fields'>,
	file: File,
	onProgress?: (percent: number) => void
): Promise<boolean> {
	const form = new FormData();

	for (const [name, value] of Object.entries(upload.fields)) {
		form.append(name, value);
	}

	// Storage only reads fields that come before the file.
	form.append('file', file);

	return new Promise((resolve) => {
		const request = new XMLHttpRequest();

		request.upload.onprogress = (event) => {
			if (event.lengthComputable) {
				onProgress?.(Math.round((event.loaded / event.total) * 100));
			}
		};

		request.onload = () => resolve(request.status >= 200 && request.status < 300);
		request.onerror = () => resolve(false);
		request.onabort = () => resolve(false);

		request.open('POST', upload.url);
		request.send(form);
	});
}
