<!--
    Register a business with its invite: its name and web address, and its
    owner's name and password (the email is the invite's). Everything else
    is filled in afterwards, in Business settings.
-->
<script lang="ts">
	import CheckboxRow from '$lib/components/forms/CheckboxRow.svelte';
	import ErrorText from '$lib/components/text/ErrorText.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { RegisterTenantRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		invite,
		email,
		siteSuffix,
		onsubmit
	}: {
		invite: string;
		email: string;
		// Shown after the web address, e.g. ".localhost:5173".
		siteSuffix: string;
		onsubmit: SubmitHandler<RegisterTenantRequest>;
	} = $props();

	let body = $state({
		business_name: '',
		code: '',
		first_name: '',
		last_name: '',
		password: '',
		terms_accepted: false
	});
	let errors = $state<FormErrors<RegisterTenantRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			// The server refuses it unless the terms are accepted (its field error shows below).
			const response = await onsubmit({ ...body, invite, terms_accepted: body.terms_accepted as true });

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Register business">
	<Field label="Business name" error={errors.business_name}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="organization" maxlength="200" bind:value={body.business_name} required />
		{/snippet}
	</Field>

	<Field label={`Web address (your site will be …${siteSuffix})`} error={errors.code}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="off" autocapitalize="none" maxlength="50" pattern="[a-z][a-z0-9\-]*" bind:value={body.code} required />
		{/snippet}
	</Field>

	<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
		<Field label="Your first name" error={errors.first_name}>
			{#snippet children(id)}
				<input {id} type="text" autocomplete="given-name" maxlength="100" bind:value={body.first_name} required />
			{/snippet}
		</Field>

		<Field label="Your last name" error={errors.last_name}>
			{#snippet children(id)}
				<input {id} type="text" autocomplete="family-name" maxlength="100" bind:value={body.last_name} required />
			{/snippet}
		</Field>
	</div>

	<Field label="Email (from your invite)">
		{#snippet children(id)}
			<input {id} type="email" value={email} readonly />
		{/snippet}
	</Field>

	<Field label="Password" error={errors.password}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="new-password" minlength="8" maxlength="128" bind:value={body.password} required />
		{/snippet}
	</Field>

	<div>
		<CheckboxRow bind:checked={body.terms_accepted} title="I accept the terms of service" />
		<ErrorText message={errors.terms_accepted} />
	</div>
</Form>
