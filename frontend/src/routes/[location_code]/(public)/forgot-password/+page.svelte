<script lang="ts">
	import { page } from '$app/state';

	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import ForgotPasswordForm from '$lib/features/auth/components/ForgotPasswordForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';

	const authApi = createAuthApi();
</script>

<Page>
	<PageHeader
		title="Reset your password"
		description="We'll email you a link to choose a new password."
	/>

	<ForgotPasswordForm onsubmit={(body) => authApi.forgotPassword(page.data.locationCode, body)} />

	<div class="flex justify-center">
		<HyperTextLink href={`/${page.data.locationCode}/login`}>
			Back to log in
		</HyperTextLink>
	</div>
</Page>
