<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import OnboardForm from '$lib/features/customer/components/OnboardForm.svelte';

	import { createCustomerApi } from '$lib/api/public/adapters/customer';
	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import type { RegistrationRequest } from '$lib/api/schema';

	let { data } = $props();

	const customerApi = createCustomerApi();

	async function register(body: RegistrationRequest) {
		const response = await customerApi.onboard(
			page.data.locationCode,
			body
		);

		if (response.ok) {
			// Give the success toast time to be read before redirecting.
			await new Promise((resolve) =>
				setTimeout(resolve, 2500)
			);

			await goto(`/${page.data.locationCode}/login`);
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
