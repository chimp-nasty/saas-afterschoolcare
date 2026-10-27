<!--
    Add someone to the location's staff: their name, email and role (only
    superadmins can choose Admin). A new account is emailed an invite to set
    their password; someone with an account already is just added.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Select from '$lib/components/forms/fields/Select.svelte';

	import type { AddStaffRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		canMakeAdmins,
		onsubmit
	}: {
		canMakeAdmins: boolean;
		onsubmit: SubmitHandler<AddStaffRequest>;
	} = $props();

	const empty: AddStaffRequest = { first_name: '', last_name: '', email: '', role: 'staff' };

	let body = $state<AddStaffRequest>({ ...empty });
	let errors = $state<FormErrors<AddStaffRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ ...body, role: canMakeAdmins ? body.role : 'staff' });

			errors = response.fieldErrors;

			if (response.ok) {
				body = { ...empty };
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Add and send invite">
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

	<Field label="Email" error={errors.email}>
		{#snippet children(id)}
			<input {id} type="email" autocomplete="off" maxlength="255" bind:value={body.email} required />
		{/snippet}
	</Field>

	{#if canMakeAdmins}
		<Field label="Role" error={errors.role}>
			{#snippet children(id)}
				<Select
					{id}
					bind:value={body.role}
					options={[
						{ value: 'staff', label: 'Staff' },
						{ value: 'admin', label: 'Admin' }
					]}
				/>
			{/snippet}
		</Field>
	{/if}
</Form>
