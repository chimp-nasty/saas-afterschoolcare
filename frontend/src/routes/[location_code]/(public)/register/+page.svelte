<script lang="ts">
	import { page } from '$app/state';
	import { goto, invalidate } from '$app/navigation';

	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import OnboardForm from '$lib/features/customer/components/OnboardForm.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';
	import { createCustomerApi } from '$lib/api/public/adapters/customer';
	import { setupHref } from '$lib/features/customer/setup';
	import { markJustRegistered } from '$lib/features/customer/welcome';
	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import type { RegistrationRequest } from '$lib/api/schema';

	let { data } = $props();

	const customerApi = createCustomerApi();
	const authApi = createAuthApi();

	async function register(body: RegistrationRequest) {
		const response = await customerApi.onboard(
			page.data.locationCode,
			body
		);

		if (response.ok) {
			// Logged straight in with what they just typed, and on to setting
			// up their account. If that fails, they log in themselves.
			const login = await authApi.login(page.data.locationCode, {
				email: body.email,
				password: body.password
			});

			if (login.ok) {
				await invalidate('app:session');
				await invalidate('app:actions-count');

				// Setup opens with a welcome explaining the steps.
				markJustRegistered();

				await goto(setupHref(page.data.locationCode));
			} else {
				await goto(`/${page.data.locationCode}/login`);
			}
		}

		return response;
	}
</script>

<Page>
	<PageHeader title="Create an account" />

	<OnboardForm termsUrl={data.hasTerms ? siteFileUrl('terms') : null} onsubmit={register} />

	<p class="text-center text-sm text-(--text-muted)">
		Already have an account?
		<HyperTextLink href={`/${page.data.locationCode}/login`}>
			Log in
		</HyperTextLink>
	</p>
</Page>
