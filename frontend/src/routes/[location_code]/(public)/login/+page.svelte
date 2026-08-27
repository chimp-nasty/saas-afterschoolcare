<script lang="ts">
	import { page } from '$app/state';
	import LoginForm from '$lib/features/auth/components/LoginForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';
    import type { LoginRequest } from '$lib/api/auth/types/types';

	let isLoading = $state(false);
	let form: LoginForm;

	const authApi = $derived(
		createAuthApi(page.data.locationCode)
	);

	async function handleLogin(body: LoginRequest) {
		try {
			isLoading = true;

			const response = await authApi.login(body);

			if (response.ok) {
				form.reset();
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<LoginForm
	bind:this={form}
	handleSubmit={handleLogin}
	{isLoading}
/>