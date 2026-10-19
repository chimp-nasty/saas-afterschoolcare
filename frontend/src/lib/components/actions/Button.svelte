<script lang="ts">
	import { getContext } from 'svelte';

	import Spinner from '$lib/components/feedback/Spinner.svelte';
	import { ACTION_BAR } from './ActionBar.svelte';

	type Variant = 'default' | 'ghost' | 'hyperlink' | 'menu';
	type TextSize = 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl';

	type Props = {
		type?: 'button' | 'submit' | 'reset';
		isLoading?: boolean;
		isDisabled?: boolean;
		isActive?: boolean;
		variant?: Variant;
		fullWidth?: boolean;
		textSize?: TextSize;
		class?: string;
		children?: () => any;
		onclick?: (event: MouseEvent) => void;
		// Required when the button only holds an icon.
		'aria-label'?: string;
	};

	let {
		type = 'button',
		isLoading = false,
		isDisabled = false,
		isActive = false,
		variant = 'default',
		fullWidth = false,
		textSize = 'xs',
		class: className = '',
		children,
		...restProps
	}: Props = $props();

	const activeClass = $derived(
		variant === 'menu' && isActive
			? `
				bg-(--primary-soft)
				text-(--primary)
				border-(--primary)
			`
			: ''
	);

	const baseClass =
		'inline-flex items-center justify-center gap-2 transition outline-none disabled:cursor-not-allowed disabled:opacity-50';

	const standardButtonClass = $derived(
		variant === 'hyperlink'
			? ''
			: 'min-h-12 tracking-wider rounded-lg px-4 font-extrabold'
	);

	// Inside an ActionBar: full width on mobile, natural width from md.
	const inActionBar = getContext<boolean>(ACTION_BAR) ?? false;

	const widthClass = $derived(
		fullWidth ? 'w-full' : inActionBar ? 'w-full md:w-fit' : 'w-fit'
	);

	// The hyperlink variant takes the size of the text around it.
	const textSizeClasses: Record<TextSize, string> = {
		xs: 'text-xs',
		sm: 'text-sm',
		base: 'text-base',
		lg: 'text-lg',
		xl: 'text-xl',
		'2xl': 'text-2xl'
	};

	const variantClasses: Record<Variant, string> = {
		default: `
			border border-(--primary)
			bg-(--primary)
			px-5 py-3
			font-extrabold uppercase tracking-wider
			text-white
			shadow-none
			hover:border-(--primary-hover)
			hover:bg-(--primary-hover)
			active:scale-[0.99]
			focus-visible:ring-0
			focus-visible:border-(--primary-hover)
			focus-visible:bg-(--primary-hover)
		`,

		ghost: `
			border border-(--border)
			bg-(--surface)
			px-5 py-3
			font-extrabold uppercase tracking-wider
			text-(--text-muted)
			shadow-none
			hover:border-(--primary)
			hover:bg-(--primary-soft)
			hover:text-(--primary)
			active:scale-[0.99]
			focus-visible:ring-0
			focus-visible:border-(--primary)
			focus-visible:bg-(--primary-soft)
			focus-visible:text-(--primary)
		`,

		hyperlink: `
			inline
			min-h-0
			justify-start
			gap-0
			rounded-none
			border-none
			bg-transparent
			p-0
			font-normal
			tracking-normal
			cursor-pointer
			text-(--hyperlink)
			shadow-none
			hover:text-(--hyperlink-hover)
			hover:underline
			active:scale-100
			focus-visible:ring-0
			focus-visible:underline
		`,

		menu: `
			min-h-0 justify-start rounded-none
			border-x-0 border-y border-(--border)
			bg-transparent
			px-5 py-3
			text-left uppercase tracking-wider
			text-(--text-muted)
			shadow-none
			hover:bg-(--primary-soft)
			hover:text-(--primary)
			active:scale-100
			focus-visible:ring-0
			focus-visible:bg-(--primary-soft)
			focus-visible:text-(--primary)
		`
	};
</script>

<button
	{type}
	class={`${baseClass} ${standardButtonClass} ${widthClass} ${variant === 'hyperlink' ? '' : textSizeClasses[textSize]} ${variantClasses[variant]} ${activeClass} ${className}`}
	disabled={isLoading || isDisabled}
	{...restProps}
>
	{@render children?.()}

	{#if isLoading}
		<Spinner isBouncy={false} />
	{/if}
</button>