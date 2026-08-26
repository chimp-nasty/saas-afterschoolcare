<script lang="ts">
	import LoginForm from '$lib/features/auth/components/LoginForm.svelte';

    import { login } from '$lib/api/auth/adapters/auth';
    import type { LoginRequest } from '$lib/api/auth/types/types';

	let isLoading = $state(false);
	let form: LoginForm;

	async function handleLogin(body: LoginRequest) {
		try {
			isLoading = true;

			const response = await login(body);

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