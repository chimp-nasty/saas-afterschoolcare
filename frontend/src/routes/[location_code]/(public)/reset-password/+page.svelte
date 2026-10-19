<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
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

<Page>
	<PageHeader title="Choose a new password" />

	{#if token}
		<ResetPasswordForm onsubmit={resetPassword} />
	{:else}
		<Card border>
			<p class="text-sm text-(--danger-text)">
				This reset link isn't valid or has expired.
			</p>
		</Card>

		<div class="flex justify-center">
			<HyperTextLink href={`/${page.data.locationCode}/forgot-password`}>
				Request a new link
			</HyperTextLink>
		</div>
	{/if}
</Page>
