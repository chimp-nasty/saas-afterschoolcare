<script lang="ts">
	import './layout.css';

	import { Toaster, toast } from 'svelte-sonner';

	import { onNavigate } from '$app/navigation';
	import { navigating, page } from '$app/state';
	import { fade } from 'svelte/transition';

	import Spinner from '$lib/components/feedback/Spinner.svelte';

	import { platformFileUrl } from '$lib/api/platform/adapters/platformSite';
	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import { isPlatformSite } from '$lib/platform/site';

	let { data, children } = $props();

	// The tab icon: the business's site icon on its site (its logo, else the
	// platform's, when it has none), the platform's own on the platform's
	// (its uploaded icon or logo, else the app's).
	const icon = $derived(isPlatformSite(page.url) ? platformFileUrl('icon') : siteFileUrl('icon'));

	// The platform's colours on every page of its own site
	// (docs/platform-site.md): set on the document, so every Layout there
	// inherits them (a business's Layout sets its own instead).
	$effect(() => {
		const site = data.platformSite;
		const style = document.documentElement.style;

		for (const [token, colour] of [
			['--primary', site?.primary_color],
			['--secondary', site?.secondary_color],
			['--accent', site?.accent_color]
		] as const) {
			if (colour) style.setProperty(token, colour);
			else style.removeProperty(token);
		}
	});

	// A page that takes a while to load shows a spinner; quick ones don't
	// flash one.
	const SPINNER_DELAY_MS = 300;

	let showSpinner = $state(false);

	$effect(() => {
		if (!navigating.to) {
			showSpinner = false;
			return;
		}

		const timer = setTimeout(() => (showSpinner = true), SPINNER_DELAY_MS);

		return () => clearTimeout(timer);
	});

	// Pages fade from one to the next (layout.css), once the next page's
	// data has loaded. Browsers without view transitions just switch.
	onNavigate((navigation) => {
		if (!document.startViewTransition) return;

		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
		});
	});

	// Tapping a toast clears it (sonner only has swiping and a close button).
	function dismissToast(event: MouseEvent) {
		if (event.target instanceof Element && event.target.closest('[data-sonner-toast]')) {
			toast.dismiss();
		}
	}
</script>

<svelte:window onclick={dismissToast} />

<svelte:head>
	<link rel="icon" href={icon} />
	<link rel="apple-touch-icon" href={icon} />
</svelte:head>

<!-- Every page's toasts, including the tenant landing page and error pages. -->
<Toaster
	position="top-center"
	duration={2000}
	toastOptions={{
		classes: {
			toast: 'cursor-pointer! rounded-2xl! border! border-(--border)! text-sm! font-extrabold!',
			success: 'bg-(--success-soft)! text-(--success-text)!',
			error: 'bg-(--danger-soft)! text-(--danger-text)!'
		}
	}}
/>

{#if showSpinner}
	<div
		class="pointer-events-none fixed inset-x-0 top-20 z-40 flex justify-center px-4"
		role="status"
		transition:fade={{ duration: 150 }}
	>
		<div
			class="flex items-center gap-2 rounded-full border border-(--border) bg-(--surface) px-4 py-2 text-sm font-semibold text-(--text) shadow-md"
		>
			<span class="text-(--primary)"><Spinner isBouncy={false} /></span>
			Loading…
		</div>
	</div>
{/if}

{@render children()}
