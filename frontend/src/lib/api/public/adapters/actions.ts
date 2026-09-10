import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type { 
    ActionResponse
} from '../types/actions';


export function createActionsApi(
    fetcher?: typeof fetch
) {
    const baseUrl =
        `${PUBLIC_API_URL}/action/v1`;

    return {
        list() {
            return apiWrapper<ActionResponse[]>(
                `${baseUrl}/`,
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
