<!--
    A staff note about one of the family's children. Never shown to the
    family; staff read it at the staff kiosk. It can't be changed once
    saved (delete it and write it again). A guide above the form says what
    belongs in a note and what doesn't.
-->
<script lang="ts">
	import ExpandableSection from '$lib/components/controls/ExpandableSection.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Select from '$lib/components/forms/fields/Select.svelte';

	import type { CreateChildNoteRequest, FamilyChildResponse } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		kids,
		onsubmit
	}: {
		// The family's current children.
		kids: FamilyChildResponse[];
		onsubmit: SubmitHandler<CreateChildNoteRequest>;
	} = $props();

	const empty = (): CreateChildNoteRequest => ({ child_id: kids.length === 1 ? kids[0].id : '', note: '' });

	let body = $state<CreateChildNoteRequest>(empty());
	let errors = $state<FormErrors<CreateChildNoteRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ ...body });

			errors = response.fieldErrors;

			if (response.ok) {
				body = empty();
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save note">
	<ExpandableSection title="What belongs in a note" defaultOpen>
		<div class="flex flex-col gap-3 text-sm text-(--text)">
			<div>
				<p class="font-semibold">Write</p>
				<ul class="list-disc pl-5">
					<li>facts staff need to care for the child day to day: "Prefers to be called Billy", "Gran collects on Fridays"</li>
					<li>what was seen or said, with no opinions or guesses</li>
				</ul>
			</div>
			<div>
				<p class="font-semibold">Don't write</p>
				<ul class="list-disc pl-5">
					<li>health details: they belong in the child's medical details, which an admin reviews</li>
					<li>judgements about the child or family, or anything about other children</li>
					<li>child protection concerns: follow the centre's procedure and report them, not here</li>
				</ul>
			</div>
			<p class="text-(--text-muted)">
				Write every note as if the family will read it. Families don't see notes in the app, but they can ask
				the centre for the records it keeps about their child.
			</p>
		</div>
	</ExpandableSection>

	<Field label="About" error={errors.child_id}>
		{#snippet children(id)}
			<Select
				{id}
				bind:value={body.child_id}
				required
				placeholder="Choose a child"
				options={kids.map((child) => ({ value: child.id, label: `${child.first_name} ${child.last_name}` }))}
			/>
		{/snippet}
	</Field>

	<Field label="Note" error={errors.note}>
		{#snippet children(id)}
			<textarea {id} rows="5" maxlength="2000" bind:value={body.note} required></textarea>
		{/snippet}
	</Field>
</Form>
