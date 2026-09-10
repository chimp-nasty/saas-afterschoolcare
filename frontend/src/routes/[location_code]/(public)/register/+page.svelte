<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import OnboardForm from '$lib/features/customer/components/OnboardForm.svelte';

	import { createCustomerApi } from '$lib/api/public/adapters/customer';
	import type { RegistrationRequest } from '$lib/api/auth/types/types';
	import type { RegistrationForm } from '$lib/features/customer/types';

	let isLoading = $state(false);
	let form: OnboardForm;

	const customerApi = createCustomerApi();

	async function handleSubmit(body: RegistrationForm) {
		const request: RegistrationRequest = {
			email: body.email,
			password: body.password,
			first_name: body.first_name,
			last_name: body.last_name,
			terms_accepted: true
		};

		try {
			isLoading = true;

			const response = await customerApi.onboard(
				page.data.locationCode,
				request
			);

			if (!response.ok) return;

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