<!--
    The business's colours (Business settings › Your site). They're the
    app's own until the owner chooses theirs; every page of the business
    uses them. Sends only the colours: the pages' words are edited inline.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import CheckboxRow from '$lib/components/forms/CheckboxRow.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { SiteRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		initial,
		onsubmit
	}: {
		initial: SiteRequest;
		onsubmit: SubmitHandler<SiteRequest>;
	} = $props();

	// The app's own colours (routes/layout.css), shown in the pickers until
	// the owner chooses theirs.
	const DEFAULT_PRIMARY = '#5e2bff';
	const DEFAULT_SECONDARY = '#e8ffc2';
	const DEFAULT_ACCENT = '#f59e0b';

	// The saved values when the form opens; it then owns its edits.
	let ownColours = $state(
		untrack(() => Boolean(initial.primary_color || initial.secondary_color || initial.accent_color))
	);
	let primary = $state(untrack(() => initial.primary_color ?? DEFAULT_PRIMARY));
	let secondary = $state(untrack(() => initial.secondary_color ?? DEFAULT_SECONDARY));
	let accent = $state(untrack(() => initial.accent_color ?? DEFAULT_ACCENT));

	let errors = $state<FormErrors<SiteRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({
				primary_color: ownColours ? primary : null,
				secondary_color: ownColours ? secondary : null,
				accent_color: ownColours ? accent : null
			});

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save">
	<CheckboxRow bind:checked={ownColours} title="Use our own colours" help="Otherwise your pages use the app's colours." />

	{#if ownColours}
		<div class="grid grid-cols-3 gap-4">
			<Field label="Main colour" error={errors.primary_color}>
				{#snippet children(id)}
					<input {id} type="color" class="h-12 w-full" bind:value={primary} />
				{/snippet}
			</Field>

			<Field label="Second colour" error={errors.secondary_color}>
				{#snippet children(id)}
					<input {id} type="color" class="h-12 w-full" bind:value={secondary} />
				{/snippet}
			</Field>

			<Field label="Accent colour" error={errors.accent_color}>
				{#snippet children(id)}
					<input {id} type="color" class="h-12 w-full" bind:value={accent} />
				{/snippet}
			</Field>
		</div>

		<p class="text-sm text-(--text-muted)">
			The main colour is for buttons and headings, the second for backgrounds (softened), and the
			accent for small highlights.
		</p>
	{/if}
</Form>
