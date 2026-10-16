<script lang="ts">
	import { page } from '$app/state';
	import { goto, invalidate } from '$app/navigation';
	import LoginForm from '$lib/features/auth/components/LoginForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';
	import type { LoginRequest } from '$lib/api/schema';

	const authApi = createAuthApi();

	async function login(body: LoginRequest) {
		const response = await authApi.login(page.data.locationCode, body);

		if (response.ok) {
			await invalidate('app:session');
			await invalidate('app:actions-count');

			await goto(`/${page.data.locationCode}/home`);
		}

		return response;
	}
</script>

<LoginForm onsubmit={login} />
