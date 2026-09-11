import { createActionsApi } from "$lib/api/public/adapters/actions";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({
    depends,
    fetch
}) => {
    const actionsApi = createActionsApi(fetch);

    const [
        actionsResponse,
    ] = await Promise.all([
        actionsApi.list(),
    ]);

    depends('app:actions');

    return {
        actions: actionsResponse.data ?? [],
    }
};