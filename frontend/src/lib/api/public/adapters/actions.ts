import { z } from 'zod';
import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type { Pagination } from '$lib/types/pagination';

import {
    actionResponseSchema,
    type ActionResponse,
    type ActionFilter
} from '../types/actions';


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
                    fetcher,
                    schema: z.array(actionResponseSchema)
                }
            );
        },

        countUncited() {
            return apiWrapper<number>(
                `${baseUrl}/count/uncited`,
                {
                    method: 'GET',
                    fetcher,
                    schema: z.number()
                }
            );
        },

        updateCitedAt(actionId: string) {
            return apiWrapper<ActionResponse>(
                `${baseUrl}/${actionId}`,
                {
                    method: 'PATCH',
                    fetcher,
                    schema: actionResponseSchema
                }
            );
        },
    }
}