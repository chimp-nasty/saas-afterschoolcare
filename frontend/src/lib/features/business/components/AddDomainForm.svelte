<!--
    Add a custom domain (Business settings › Domains): the business's main
    domain, or one sending visitors to it. The server writes the name the
    way DNS does and checks it isn't one of the platform's.
-->
<script lang="ts">
	import CheckboxRow from '$lib/components/forms/CheckboxRow.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { AddDomainRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		isMain,
		onsubmit
	}: {
		isMain: boolean;
		onsubmit: SubmitHandler<AddDomainRequest>;
	} = $props();

	let hostname = $state('');
	let includeWww = $state(true);

	let errors = $state<FormErrors<AddDomainRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ hostname, is_main: isMain, include_www: includeWww });

			errors = response.fieldErrors;

			if (response.ok) {
				hostname = '';
				includeWww = true;
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel={isMain ? 'Add main domain' : 'Add domain'}>
	<Field label="Domain (e.g. after3.com.au)" error={errors.hostname}>
		{#snippet children(id)}
			<input {id} type="text" inputmode="url" autocomplete="off" autocapitalize="none" maxlength="253" bind:value={hostname} required />
		{/snippet}
	</Field>

	<CheckboxRow bind:checked={includeWww} title="Include www too" help="So www.yourdomain works as well. Not needed if what you typed starts with www." />
</Form>
