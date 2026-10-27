<!--
    A single choice from a list, in place of a native <select> (which each
    phone and browser draws its own way). Used like one inside Field: it
    takes the snippet's `id`, and `bind:value` or `onchange`. A trigger styled
    like the other underline inputs opens a list of 44px rows below it, the
    chosen one ticked.

    Keyboard: Enter, Space or the arrows open it; the arrows, Home and End
    move; Enter or Space chooses; Escape or Tab closes. `required` is checked
    by the form like a native field's.
-->
<script lang="ts" module>
	export type SelectOption = {
		value: string;
		label: string;
		disabled?: boolean;
	};
</script>

<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { Check, ChevronDown } from 'lucide-svelte';

	type Props = {
		value?: string;
		options: SelectOption[];
		id?: string;
		// Shown while nothing in `options` is chosen.
		placeholder?: string;
		required?: boolean;
		disabled?: boolean;
		onchange?: (value: string) => void;
		// When there's no Field label (e.g. a filter).
		'aria-label'?: string;
		// The kiosk tablet, read at arm's length: one size up.
		size?: 'default' | 'kiosk';
		class?: string;
	};

	let {
		value = $bindable(''),
		options,
		id,
		placeholder = 'Select an option',
		required = false,
		disabled = false,
		onchange,
		'aria-label': ariaLabel,
		size = 'default',
		class: className = ''
	}: Props = $props();

	const listId = $props.id();

	let container: HTMLDivElement;
	let trigger: HTMLButtonElement;
	let list = $state<HTMLDivElement>();

	let isOpen = $state(false);
	// The row the arrow keys are on.
	let highlighted = $state(-1);

	const selected = $derived(options.find((option) => option.value === value));

	const textSize = $derived(size === 'kiosk' ? 'text-lg' : 'text-base');

	function enabledIndexes(): number[] {
		return options.flatMap((option, index) => (option.disabled ? [] : [index]));
	}

	async function open() {
		if (disabled) return;

		isOpen = true;

		const current = options.findIndex((option) => option.value === value && !option.disabled);
		highlighted = current >= 0 ? current : (enabledIndexes()[0] ?? -1);

		await tick();
		list?.querySelector(`[data-index="${highlighted}"]`)?.scrollIntoView({ block: 'nearest' });
	}

	function close() {
		isOpen = false;
		highlighted = -1;
	}

	function choose(option: SelectOption) {
		if (option.disabled) return;

		close();
		trigger.focus();

		if (option.value === value) return;

		value = option.value;
		onchange?.(option.value);
	}

	function move(step: 1 | -1 | 'first' | 'last') {
		const indexes = enabledIndexes();

		if (indexes.length === 0) return;

		const position = indexes.indexOf(highlighted);

		highlighted =
			step === 'first'
				? indexes[0]
				: step === 'last'
					? indexes[indexes.length - 1]
					: indexes[Math.min(Math.max(position + step, 0), indexes.length - 1)];

		list?.querySelector(`[data-index="${highlighted}"]`)?.scrollIntoView({ block: 'nearest' });
	}

	function keydown(event: KeyboardEvent) {
		if (!isOpen) {
			if (['Enter', ' ', 'ArrowDown', 'ArrowUp'].includes(event.key)) {
				event.preventDefault();
				void open();
			}

			return;
		}

		switch (event.key) {
			case 'ArrowDown':
				event.preventDefault();
				move(1);
				break;
			case 'ArrowUp':
				event.preventDefault();
				move(-1);
				break;
			case 'Home':
				event.preventDefault();
				move('first');
				break;
			case 'End':
				event.preventDefault();
				move('last');
				break;
			case 'Enter':
			case ' ':
				event.preventDefault();
				if (options[highlighted]) choose(options[highlighted]);
				break;
			case 'Escape':
				event.preventDefault();
				close();
				break;
			case 'Tab':
				close();
				break;
		}
	}

	onMount(() => {
		// pointerdown, not mousedown, so taps on phones close it too.
		function outside(event: PointerEvent) {
			if (isOpen && !container.contains(event.target as Node)) close();
		}

		document.addEventListener('pointerdown', outside);

		return () => document.removeEventListener('pointerdown', outside);
	});
</script>

<div class={['relative', className]} bind:this={container}>
	<button
		bind:this={trigger}
		{id}
		type="button"
		{disabled}
		role="combobox"
		aria-label={ariaLabel}
		aria-haspopup="listbox"
		aria-expanded={isOpen}
		aria-controls={listId}
		aria-activedescendant={isOpen && highlighted >= 0 ? `${listId}-${highlighted}` : undefined}
		onclick={() => (isOpen ? close() : open())}
		onkeydown={keydown}
		class={[
			'flex min-h-11 w-full items-center justify-between gap-2 border-b py-2 text-left transition outline-none disabled:cursor-not-allowed disabled:opacity-65',
			textSize,
			isOpen ? 'border-(--primary)' : 'border-(--border) focus-visible:border-(--primary)',
			selected ? 'text-(--text)' : 'text-(--text-muted)'
		]}
	>
		<span class="truncate">{selected?.label ?? placeholder}</span>

		<ChevronDown
			size={18}
			class={`shrink-0 text-(--text-muted) transition-transform ${isOpen ? 'rotate-180' : ''}`}
		/>
	</button>

	<!-- For the form's own `required` check; tells the user via the trigger. -->
	{#if required}
		<input
			class="pointer-events-none absolute bottom-0 left-0 h-px! w-px! opacity-0"
			tabindex="-1"
			aria-hidden="true"
			{required}
			value={selected ? value : ''}
			oninvalid={() => trigger.focus()}
		/>
	{/if}

	{#if isOpen}
		<div
			bind:this={list}
			id={listId}
			role="listbox"
			class="absolute inset-x-0 z-50 mt-1 flex max-h-72 flex-col overflow-y-auto rounded-2xl border border-(--border) bg-(--surface) p-2 shadow-sm"
		>
			{#each options as option, index (option.value)}
				<!-- Focus stays on the trigger (aria-activedescendant), so the
				     rows only take pointer input. -->
				<div
					id={`${listId}-${index}`}
					data-index={index}
					role="option"
					tabindex="-1"
					aria-selected={option.value === value}
					aria-disabled={option.disabled}
					onpointerenter={() => !option.disabled && (highlighted = index)}
					onclick={() => choose(option)}
					onkeydown={() => {}}
					class={[
						'flex min-h-11 cursor-pointer items-center justify-between gap-3 rounded-lg px-3',
						textSize,
						option.value === value ? 'font-semibold text-(--primary)' : 'text-(--text)',
						index === highlighted && 'bg-(--surface-muted)',
						option.disabled && 'cursor-not-allowed opacity-50'
					]}
				>
					<span class="min-w-0 truncate">{option.label}</span>

					{#if option.value === value}
						<Check size={18} class="shrink-0" />
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>
