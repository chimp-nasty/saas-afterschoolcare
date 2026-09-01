<script lang="ts">
	import { page } from '$app/state';
	import { goto, invalidate } from '$app/navigation';
	import LoginForm from '$lib/features/auth/components/LoginForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';
    import type { LoginRequest } from '$lib/api/auth/types/types';

	let isLoading = $state(false);
	let form: LoginForm;

	const authApi = createAuthApi();

	async function handleSubmit(body: LoginRequest) {
		try {
			isLoading = true;

			const response = await authApi.login(page.data.locationCode, body);

			if (!response.ok) {
				return;
			}

			form.reset();

			await invalidate('app:session');
			await goto(`/${page.data.locationCode}/home`);
		} finally {
			isLoading = false;
		}
	}
</script>

<LoginForm
	bind:this={form}
	{handleSubmit}
	{isLoading}
/>