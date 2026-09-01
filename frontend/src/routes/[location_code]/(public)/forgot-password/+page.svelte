<script lang="ts">
	import ForgotPasswordForm from '$lib/features/auth/components/ForgotPasswordForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';

	let isLoading = $state(false);
	let form: ForgotPasswordForm;

	const authApi = createAuthApi();

	async function handleSubmit(
		body: {
			email: string;
		}
	) {
		try {
			isLoading = true;

			const response = await authApi.forgotPassword(body);

			if (response.ok) {
				form.reset();
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<ForgotPasswordForm
	bind:this={form}
	{handleSubmit}
	{isLoading}
/>