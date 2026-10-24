import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	ChildDocumentDownloadResponse,
	ChildDocumentResponse,
	ChildDocumentUploadResponse,
	CreateChildDocumentRequest
} from '$lib/api/schema';


export function createChildDocumentsApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/child-documents/v1`;

	return {
		// The child's current documents, newest first.
		list(childId: string) {
			return apiWrapper<ChildDocumentResponse[]>(
				`${baseUrl}/?child_id=${encodeURIComponent(childId)}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		// Step 1 of an upload: returns where to send the file
		// (uploadToStorage), then call complete.
		start(
			body: CreateChildDocumentRequest
		) {
			return apiWrapper<ChildDocumentUploadResponse>(
				`${baseUrl}/`,
				{
					method: 'POST',
					body,
					fetcher,
					quiet: true
				}
			);
		},

		// Step 3: the server checks the stored file and accepts it.
		complete(documentId: string) {
			return apiWrapper<ChildDocumentResponse>(
				`${baseUrl}/${documentId}/complete`,
				{
					method: 'POST',
					fetcher
				}
			);
		},

		// A link to view the file, valid for a few minutes.
		download(documentId: string) {
			return apiWrapper<ChildDocumentDownloadResponse>(
				`${baseUrl}/${documentId}/download`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		remove(documentId: string) {
			return apiWrapper<ChildDocumentResponse>(
				`${baseUrl}/${documentId}/remove`,
				{
					method: 'POST',
					fetcher
				}
			);
		}
	};
}
