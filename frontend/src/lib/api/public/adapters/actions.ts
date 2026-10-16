import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type { Pagination } from '$lib/types/pagination';

import type {
    operations,
    ActionResponse
} from '$lib/api/schema';


export type ActionFilter = Omit<
    NonNullable<operations['list_actions_action_v1__get']['parameters']['query']>,
    keyof Pagination
>;


export function createActionsApi(
    fetcher?: typeof fetch
) {
    const baseUrl =
        `${PUBLIC_API_URL}/action/v1`;

    return {
        list(
            filters: ActionFilter = {},
            pagination: Pagination = {}
        ) {
            const query = buildQueryParams(
                filters,
                pagination
            );

            return apiWrapper<ActionResponse[]>(
                `${baseUrl}/${query ? `?${query}` : ''}`,
                {
                    method: 'GET',
                    fetcher
                }
            );
        },

        countUncited() {
            return apiWrapper<number>(
                `${baseUrl}/count/uncited`,
                {
                    method: 'GET',
                    fetcher
                }
            );
        },

        updateCitedAt(actionId: string) {
            return apiWrapper<ActionResponse>(
                `${baseUrl}/${actionId}`,
                {
                    method: 'PATCH',
                    fetcher
                }
            );
        },
    }
}
