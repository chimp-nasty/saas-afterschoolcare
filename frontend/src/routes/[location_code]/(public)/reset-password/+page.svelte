<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import ErrorText from '$lib/components/text/ErrorText.svelte';
	import ResetPasswordForm from '$lib/features/auth/components/ResetPasswordForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';

	const token = $derived(
		page.url.searchParams.get('token')
	);

	// A staff invite uses the same single-use link to set a first password.
	const isInvite = $derived(page.url.searchParams.get('invite') === '1');

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
	<PageHeader
		title={isInvite ? 'Set your password' : 'Choose a new password'}
		description={isInvite ? "Welcome aboard. Choose a password, then log in." : undefined}
	/>

	{#if token}
		<ResetPasswordForm onsubmit={resetPassword} />
	{:else}
		<Card border>
			<ErrorText
				message={isInvite
					? "This link isn't valid or has expired. Ask the centre to send a new invite."
					: "This link isn't valid or has expired."}
			/>
		</Card>

		<div class="flex justify-center">
			<HyperTextLink href={`/${page.data.locationCode}/forgot-password`}>
				Request a new link
			</HyperTextLink>
		</div>
	{/if}
</Page>
