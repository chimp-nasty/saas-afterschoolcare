import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type {
	operations,
	MedicalReviewDecisionRequest,
	MedicalReviewResponse,
	MedicalReviewSummaryResponse
} from '$lib/api/schema';


export type ListMedicalReviewsFilter = NonNullable<
	operations['list_medical_reviews_medical_reviews_v1__get']['parameters']['query']
>;


export function createMedicalReviewsApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/medical-reviews/v1`;

	return {
		// Children waiting on staff or their family (by default), longest
		// waiting first.
		list(
			filters: ListMedicalReviewsFilter = {}
		) {
			const query = buildQueryParams(filters);

			return apiWrapper<MedicalReviewSummaryResponse[]>(
				`${baseUrl}/${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		get(childId: string) {
			return apiWrapper<MedicalReviewResponse>(
				`${baseUrl}/${childId}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		decide(
			childId: string,
			body: MedicalReviewDecisionRequest
		) {
			return apiWrapper<MedicalReviewResponse>(
				`${baseUrl}/${childId}`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		}
	};
}
