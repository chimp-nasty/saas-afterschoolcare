<!--
    Deactivate your family account at this centre: your password again (so
    it's really you), then the page asks to confirm. The server checks the
    password and that there are no upcoming bookings
    (docs/account-deactivation.md).
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { DeactivateAccountRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<DeactivateAccountRequest>;
	} = $props();

	let body = $state<DeactivateAccountRequest>({ password: '' });
	let errors = $state<FormErrors<DeactivateAccountRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ ...body });

			errors = response.fieldErrors;

			if (response.ok) {
				body = { password: '' };
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Deactivate account">
	<Field label="Your password" error={errors.password}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="current-password" bind:value={body.password} required />
		{/snippet}
	</Field>
</Form>
