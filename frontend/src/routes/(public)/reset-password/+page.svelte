<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	import ResetPasswordForm from '$lib/features/auth/components/ResetPasswordForm.svelte';

	import { resetPassword } from '$lib/api/auth/adapters/auth';

	let isLoading = $state(false);
	let form = $state<ResetPasswordForm | null>(null);

	const token = $derived(
		page.url.searchParams.get('token')
	);

	async function handleSubmit(
		password: string
	) {
		if (!token) {
			return;
		}

		try {
			isLoading = true;

			const response = await resetPassword({
				token,
				password
			});

			if (response.ok && form) {
				form.reset();

				await goto('/login');
			}
		} finally {
			isLoading = false;
		}
	}
</script>

{#if token}
	<ResetPasswordForm
		bind:this={form}
		{handleSubmit}
		{isLoading}
	/>
{:else}
	<p class="text-sm text-(--danger-text)">
		Invalid password reset link.
	</p>
{/if}