<script lang="ts">
	import './layout.css';

	import { Toaster, toast } from 'svelte-sonner';

	import { page } from '$app/state';

	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import { isPlatformSite } from '$lib/platform/site';

	let { children } = $props();

	// The tab icon: the business's site icon on its site (its logo, else the
	// platform's, when it has none), the platform's own on the platform's.
	const icon = $derived(isPlatformSite(page.url) ? '/favicon.svg' : siteFileUrl('icon'));

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

{@render children()}
