<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	import ResetPasswordForm from '$lib/features/auth/components/ResetPasswordForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';

	const token = $derived(
		page.url.searchParams.get('token')
	);

	const authApi = createAuthApi();

	async function resetPassword(password: string) {
		const response = await authApi.resetPassword({
			token: token ?? '',
			password
		});

		if (response.ok) {
			await goto(`/${page.data.locationCode}/login`);
		}

		return response;
	}
</script>

{#if token}
	<ResetPasswordForm onsubmit={resetPassword} />
{:else}
	<p class="text-sm text-(--danger-text)">
		Invalid password reset link.
	</p>
{/if}
