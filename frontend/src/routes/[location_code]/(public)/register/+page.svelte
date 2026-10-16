<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import OnboardForm from '$lib/features/customer/components/OnboardForm.svelte';

	import { createCustomerApi } from '$lib/api/public/adapters/customer';
	import type { RegistrationRequest } from '$lib/api/schema';

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

<OnboardForm onsubmit={register} />
