<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import OnboardForm from '$lib/features/customer/components/OnboardForm.svelte';

	import { createCustomerApi } from '$lib/api/public/adapters/customer';
    import type { RegistrationRequest } from '$lib/api/auth/types/types';

	let isLoading = $state(false);
	let form: OnboardForm;

	const customerApi = createCustomerApi();

	async function handleSubmit(body: RegistrationRequest) {
		try {
			isLoading = true;

			const response = await customerApi.onboard(page.data.locationCode, body);

			if (!response.ok) {
				return;
			}

			form.reset();
			
			await new Promise((resolve) =>
				setTimeout(resolve, 2500)
			);

			await goto(`/${page.data.locationCode}/login`);
		} finally {
			isLoading = false;
		}
	}
</script>

<OnboardForm
	bind:this={form}
	{handleSubmit}
	{isLoading}
/>