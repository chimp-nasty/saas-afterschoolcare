<!--
    The site's header, kept at the top of every page by Layout
    (docs/public-site.md, section 2): the logo and name (a link home), then

    - from md: `links` in a row, then `desktopActions` (e.g. Log in, Enrol now)
    - always: `actions` (e.g. the bell)
    - on a phone: a menu button opening a drawer from the right with
      `menuLead` (e.g. Log in, or a family's Home and Bookings), `links`, then
      `menuItems` (e.g. Log out) as rows; a link already in `menuLead` isn't
      repeated

    Staff and admins pass `onMenu` instead, and their menu button opens the
    sidebar's drawer.
-->
<script lang="ts" module>
	export type HeaderLink = { label: string; href: string };
	// A link (href) or an action (onclick, e.g. Log out).
	export type HeaderMenuItem = { label: string; href?: string; onclick?: () => void };
</script>

<script lang="ts">
	import type { Snippet } from 'svelte';
	import { afterNavigate } from '$app/navigation';

	import { Menu } from 'lucide-svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';

	let {
		homeHref,
		title,
		hasLogo,
		links = [],
		menuLead = [],
		menuItems = [],
		actions,
		desktopActions,
		note,
		onMenu,
		flush = false
	}: {
		// Where the logo and name go.
		homeHref: string;
		title: string;
		hasLogo: boolean;
		links?: HeaderLink[];
		// The phone drawer only: before the links, and after them.
		menuLead?: HeaderMenuItem[];
		menuItems?: HeaderMenuItem[];
		actions?: Snippet;
		desktopActions?: Snippet;
		// A line shown from md, before the actions (e.g. who's logged in).
		note?: string | null;
		// Opens the staff drawer instead of this one.
		onMenu?: () => void;
		// Above a public site page's bands (Layout's flush): no gap below.
		flush?: boolean;
	} = $props();

	// How long the drawer takes to slide away (the CSS below), before the
	// dialog itself closes.
	const CLOSE_MS = 420;

	let dialog = $state<HTMLDialogElement>();
	// Drives the slide and fades; the dialog is open a moment before and
	// after, so the transitions have something to run on.
	let visible = $state(false);

	const rows = $derived<HeaderMenuItem[]>([
		...menuLead,
		...links.filter((link) => !menuLead.some((item) => item.href === link.href)),
		...menuItems
	]);

	function open() {
		if (onMenu) {
			onMenu();
			return;
		}

		dialog?.showModal();
		document.documentElement.style.overflow = 'hidden';

		requestAnimationFrame(() => {
			visible = true;
		});
	}

	function close() {
		if (!dialog?.open) return;

		visible = false;

		setTimeout(() => {
			dialog?.close();
			document.documentElement.style.overflow = '';
		}, CLOSE_MS);
	}

	// Following a link (or logging out) closes the drawer.
	afterNavigate(close);

	// Escape: slide away rather than vanish.
	function cancel(event: Event) {
		event.preventDefault();
		close();
	}

	// A tap on the dimmed page beside the panel.
	function clickOutside(event: MouseEvent) {
		if (!dialog || event.target !== dialog) return;

		const panel = dialog.getBoundingClientRect();

		if (event.clientX < panel.left) close();
	}

	function choose(item: HeaderMenuItem) {
		close();
		item.onclick?.();
	}
</script>

<header
	class={[
		!flush && 'mb-6',
		'w-full border-b border-(--border) bg-(--surface)/90 backdrop-blur-md'
	]}
>
	<div class="mx-auto flex min-h-16 w-full max-w-6xl items-center gap-4 px-4 py-2">
		<a href={homeHref} class="mr-auto flex min-h-11 min-w-0 items-center gap-3 rounded-lg">
			{#if hasLogo}
				<img src={siteFileUrl('logo')} alt="" class="h-9 w-auto max-w-32 object-contain" />
			{/if}

			<span class="truncate text-sm font-semibold text-(--text)">{title}</span>
		</a>

		{#if links.length > 0}
			<!-- Links with a dot between them (the accent colour, decoration
			     only). Hovering one nudges it right, turns it the main colour
			     and underlines it in the accent. -->
			<nav class="hidden items-center gap-3 md:flex" aria-label="Site">
				{#each links as link, index (link.href)}
					{#if index > 0}
						<span class="size-1.5 shrink-0 rounded-full bg-(--accent)" aria-hidden="true"></span>
					{/if}

					<a
						href={link.href}
						class="flex min-h-11 items-center px-1 text-sm font-semibold text-(--text) decoration-(--accent) decoration-2 underline-offset-[6px] transition duration-200 hover:text-(--primary) hover:underline focus-visible:text-(--primary) focus-visible:underline motion-safe:hover:translate-x-1"
					>
						{link.label}
					</a>
				{/each}
			</nav>
		{/if}

		{#if note}
			<p class="hidden text-sm text-(--text-muted) md:block">{note}</p>
		{/if}

		{#if desktopActions}
			<div class="hidden items-center gap-2 md:flex">
				{@render desktopActions()}
			</div>
		{/if}

		{@render actions?.()}

		{#if onMenu || rows.length > 0}
			<div class="md:hidden">
				<Button variant="ghost" onclick={open} aria-label="Menu">
					<Menu size={20} />
				</Button>
			</div>
		{/if}
	</div>
</header>

{#if !onMenu && rows.length > 0}
	<dialog
		bind:this={dialog}
		class={['drawer md:hidden', visible && 'visible']}
		aria-label="Menu"
		oncancel={cancel}
		onclick={clickOutside}
	>
		<div class="flex min-h-full flex-col px-7 pt-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]">
			<div class="flex items-center justify-between gap-4">
				<p class="label-text truncate">{title}</p>

				<button
					type="button"
					class="flex min-h-11 items-center gap-2 rounded-full border border-(--border) px-4 text-xs font-extrabold tracking-wide text-(--text) uppercase"
					onclick={close}
				>
					Close <span class="text-lg leading-none" aria-hidden="true">×</span>
				</button>
			</div>

			<span class="mt-8 mb-4 h-1 w-10 rounded-full bg-(--accent)" aria-hidden="true"></span>

			<nav class="grid" aria-label="Menu">
				{#each rows as item, index (item.label)}
					{#if item.href}
						<a href={item.href} class="drawer-row" onclick={close}>
							<small aria-hidden="true">{String(index + 1).padStart(2, '0')}</small>
							<span>{item.label}</span>
						</a>
					{:else}
						<button type="button" class="drawer-row" onclick={() => choose(item)}>
							<small aria-hidden="true">{String(index + 1).padStart(2, '0')}</small>
							<span>{item.label}</span>
						</button>
					{/if}
				{/each}
			</nav>
		</div>
	</dialog>
{/if}

<style>
	/* A panel from the right, over a dimmed and blurred page. */
	.drawer {
		position: fixed;
		inset: 0;
		width: min(88vw, 390px);
		max-width: none;
		height: 100dvh;
		max-height: none;
		margin: 0 0 0 auto;
		padding: 0;
		overflow: auto;
		border: 0;
		border-left: 1px solid var(--border);
		background: var(--surface);
		color: var(--text);
		box-shadow: -12px 0 40px rgb(0 0 0 / 0.12);
		opacity: 0;
		transform: translateX(105%);
		transition:
			transform 0.42s cubic-bezier(0.22, 0.8, 0.2, 1),
			opacity 0.3s;
	}

	.drawer::backdrop {
		background: var(--overlay);
		backdrop-filter: blur(3px);
		opacity: 0;
		transition: opacity 0.35s;
	}

	.drawer.visible {
		opacity: 1;
		transform: none;
	}

	.drawer.visible::backdrop {
		opacity: 1;
	}

	.drawer-row {
		display: flex;
		align-items: center;
		gap: 1rem;
		min-height: 4rem;
		padding: 0.5rem 0;
		border-bottom: 1px solid var(--border);
		color: var(--text);
		text-align: left;
		transition: color 0.18s;
	}

	.drawer-row:hover,
	.drawer-row:focus-visible {
		color: var(--primary);
	}

	.drawer-row small {
		font-size: 0.625rem;
		letter-spacing: 0.08em;
		color: var(--text-muted);
	}

	.drawer-row span {
		font-size: 1.625rem;
		font-weight: 800;
		letter-spacing: -0.02em;
	}

	@media (prefers-reduced-motion: reduce) {
		.drawer,
		.drawer::backdrop,
		.drawer-row {
			transition: none;
		}
	}
</style>
