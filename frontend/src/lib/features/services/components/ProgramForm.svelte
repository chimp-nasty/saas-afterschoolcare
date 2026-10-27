<!--
    A program's text, edited inline on the centre's programs page
    (EditableSection): its description and the four parts after it. Sends
    only these, so the service's price, times and policies are left as they
    are; a part left blank is cleared and disappears from the page.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { LocationServiceSelectionResponse, UpdateLocationServiceConfigRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';
	import { PROGRAM_FIELDS, type ProgramField } from '../program';

	type ProgramRequest = Pick<UpdateLocationServiceConfigRequest, 'description' | ProgramField>;

	let {
		service,
		onsubmit,
		oncancel
	}: {
		service: LocationServiceSelectionResponse;
		onsubmit: SubmitHandler<ProgramRequest>;
		oncancel?: () => void;
	} = $props();

	// What each part asks for, under its heading.
	const PLACEHOLDERS: Record<ProgramField, string> = {
		inclusions: 'e.g. Afternoon tea and all activity materials',
		drop_off_pickup: 'e.g. Where children go after the bell, and where and when to collect them',
		what_to_bring: 'e.g. A water bottle and a hat',
		activities: 'e.g. Sport, art, games and a quiet study space'
	};

	// The saved text when the form opens; it then owns its edits.
	let body = $state<Record<'description' | ProgramField, string>>(
		untrack(() => ({
			description: service.description ?? '',
			inclusions: service.inclusions ?? '',
			drop_off_pickup: service.drop_off_pickup ?? '',
			what_to_bring: service.what_to_bring ?? '',
			activities: service.activities ?? ''
		}))
	);

	let errors = $state<FormErrors<ProgramRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ ...body });

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel={`Save ${service.service_name}`} {oncancel}>
	<Field label="Description: what it is, in a sentence or two" error={errors.description}>
		{#snippet children(id)}
			<textarea {id} rows="3" maxlength="1000" bind:value={body.description}></textarea>
		{/snippet}
	</Field>

	{#each PROGRAM_FIELDS as { field, label } (field)}
		<Field {label} error={errors[field]}>
			{#snippet children(id)}
				<textarea {id} rows="3" maxlength="2000" placeholder={PLACEHOLDERS[field]} bind:value={body[field]}></textarea>
			{/snippet}
		</Field>
	{/each}

	<p class="text-sm text-(--text-muted)">Leave a part empty to leave it off the page. Price, times and ages are in Service settings.</p>
</Form>
