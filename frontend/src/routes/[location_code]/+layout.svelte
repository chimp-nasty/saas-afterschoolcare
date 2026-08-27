<script lang="ts">
	import { onMount } from 'svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';
	import { setSession, clearSession } from '$lib/auth/state.svelte';

	let { data, children } = $props();

	onMount(async () => {
		const authApi = createAuthApi(data.locationCode);
		const response = await authApi.getSession();

		if (response.ok && response.data) {
			setSession({
				userId: response.data.user_id,
				tenantId: response.data.location_id,
				email: response.data.email,
				firstName: response.data.first_name,
				roles: response.data.roles
			});
		} else {
			clearSession();
		}
	});
</script>

{@render children()}
