<script lang="ts">
	import type { Snippet } from 'svelte';

	import Card from '$lib/components/layout/Card.svelte';
	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';

	type Props = {
		handleSubmit: () => void | Promise<void>;
		isLoading: boolean;
		children: Snippet;
		submitLabel?: string;
		fullWidth?: boolean;
		// A Cancel beside the submit button (e.g. an inline editor going
		// back to its section, EditableSection).
		oncancel?: () => void;
	};

	let {
		handleSubmit,
		isLoading,
		children,
		submitLabel = 'Submit',
		fullWidth = true,
		oncancel
	}: Props = $props();
</script>

<!-- Takes the width of the Page it's in. -->
<Card border={true}>
	<form
		onsubmit={(event) => {
			event.preventDefault();
			void handleSubmit();
		}}
	>
		<div class="flex flex-col gap-4">
			{@render children()}

			<div class="mt-2">
				{#if oncancel}
					<ActionBar>
						<Button variant="ghost" isDisabled={isLoading} onclick={oncancel}>Cancel</Button>
						<Button type="submit" {isLoading} isDisabled={isLoading}>{submitLabel}</Button>
					</ActionBar>
				{:else}
					<Button
						type="submit"
						{isLoading}
						{fullWidth}
						isDisabled={isLoading}
					>
						{submitLabel}
					</Button>
				{/if}
			</div>
		</div>
	</form>
</Card>
