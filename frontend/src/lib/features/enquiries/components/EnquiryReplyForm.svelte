<!--
    An admin's reply to an enquiry. It's emailed to the person exactly as
    written (the one email with a staff member's own words,
    docs/email-policy.md), so the box says what not to put in it.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Notice from '$lib/components/text/Notice.svelte';

	import type { EnquiryReplyRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<EnquiryReplyRequest>;
	} = $props();

	let body = $state<EnquiryReplyRequest>({ body: '' });
	let errors = $state<FormErrors<EnquiryReplyRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ ...body });

			errors = response.fieldErrors;

			if (response.ok) body = { body: '' };
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Send reply">
	<Notice tone="warning">
		This is emailed to them as you write it. Don't include health or medical details, or children's surnames.
	</Notice>

	<Field label="Your reply" error={errors.body}>
		{#snippet children(id)}
			<textarea {id} rows="6" maxlength="3000" bind:value={body.body} required></textarea>
		{/snippet}
	</Field>
</Form>
