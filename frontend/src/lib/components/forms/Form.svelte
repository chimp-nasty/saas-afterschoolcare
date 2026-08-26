<script lang="ts">
	import type { Snippet } from 'svelte';

    import Card from '$lib/components/layout/Card.svelte';
	import Button from '$lib/components/actions/Button.svelte';

	type Props = {
		handleSubmit: () => void | Promise<void>;
		isLoading: boolean;
		children: Snippet;
		submitLabel?: string;
		fullWidth?: boolean;
	};

	let {
		handleSubmit,
		isLoading,
		children,
		submitLabel = 'Submit',
		fullWidth = true
	}: Props = $props();
</script>

<Card>
    <form
        onsubmit={(event) => {
            event.preventDefault();
            void handleSubmit();
        }}
    >
        <div class="flex flex-col gap-2">
            {@render children()}

            <div class="mt-2">
                <Button
                    type="submit"
                    {isLoading}
                    {fullWidth}
                    isDisabled={isLoading}
                >
                    {submitLabel}
                </Button>
            </div>
        </div>
    </form>
</Card>