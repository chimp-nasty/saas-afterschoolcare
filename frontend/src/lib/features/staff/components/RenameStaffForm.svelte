<!--
    Correct a staff member's name (staff can't change their own: their
    account page is read-only).
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { RenameStaffRequest, StaffAccountResponse } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type RenameForm = { first_name: string; last_name: string };

	let {
		staff,
		onsubmit
	}: {
		staff: StaffAccountResponse;
		onsubmit: SubmitHandler<RenameStaffRequest>;
	} = $props();

	// Initial values only.
	function toForm(): RenameForm {
		return { first_name: staff.first_name, last_name: staff.last_name };
	}

	let body = $state<RenameForm>(toForm());
	let errors = $state<FormErrors<RenameForm>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			errors = (await onsubmit(body)).fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save name">
	<div class="grid grid-cols-2 gap-4">
		<Field label="First name" error={errors.first_name}>
			{#snippet children(id)}
				<input {id} type="text" autocomplete="off" maxlength="100" bind:value={body.first_name} required />
			{/snippet}
		</Field>
		<Field label="Last name" error={errors.last_name}>
			{#snippet children(id)}
				<input {id} type="text" autocomplete="off" maxlength="100" bind:value={body.last_name} required />
			{/snippet}
		</Field>
	</div>
</Form>
