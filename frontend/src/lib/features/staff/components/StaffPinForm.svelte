<!--
    Set or change your staff kiosk PIN: your password (to confirm it's you),
    then the new 4-digit PIN twice. The match check is the only one here; the
    server checks the password and the PIN's format.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { SetStaffPinRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type StaffPinForm = {
		password: string;
		pin: string;
		confirm_pin: string;
	};

	let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<SetStaffPinRequest>;
	} = $props();

	const empty: StaffPinForm = { password: '', pin: '', confirm_pin: '' };

	let body = $state<StaffPinForm>({ ...empty });
	let errors = $state<FormErrors<StaffPinForm>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};

		if (body.pin !== body.confirm_pin) {
			errors = { confirm_pin: "The PINs don't match." };
			return;
		}

		isLoading = true;

		try {
			const response = await onsubmit({ password: body.password, pin: body.pin });

			errors = response.fieldErrors;

			if (response.ok) {
				body = { ...empty };
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save PIN">
	<Field label="Your password" error={errors.password}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="current-password" bind:value={body.password} required />
		{/snippet}
	</Field>

	<Field label="New PIN (4 digits)" error={errors.pin}>
		{#snippet children(id)}
			<input
				{id}
				type="password"
				inputmode="numeric"
				autocomplete="off"
				pattern={"[0-9]{4}"}
				minlength="4"
				maxlength="4"
				bind:value={body.pin}
				required
			/>
		{/snippet}
	</Field>

	<Field label="New PIN again" error={errors.confirm_pin}>
		{#snippet children(id)}
			<input
				{id}
				type="password"
				inputmode="numeric"
				autocomplete="off"
				pattern={"[0-9]{4}"}
				minlength="4"
				maxlength="4"
				bind:value={body.confirm_pin}
				required
			/>
		{/snippet}
	</Field>
</Form>
