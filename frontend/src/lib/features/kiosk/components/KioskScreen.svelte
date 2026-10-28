<!--
    The kiosk's full screen: the centre's logo and name across the top, an
    optional right-hand area (e.g. "Logged in as Jo · Done"), the live
    date and time, and the current step. Large text throughout: it's read
    standing up, at arm's length.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import KioskClock from './KioskClock.svelte';

	let {
		centreName,
		hasLogo = false,
		label,
		actions,
		children
	}: {
		centreName: string;
		// The business's logo beside the name, when it has one.
		hasLogo?: boolean;
		// Which kiosk, before the centre's name ("Family kiosk", "Staff kiosk").
		label?: string;
		actions?: Snippet;
		children: Snippet;
	} = $props();
</script>

<div class="flex min-h-[calc(100dvh-2rem)] flex-col gap-6">
	<!-- Frozen at the top while the step below scrolls (long rolls, many
	     children), over the page's padding so nothing shows above it. -->
	<header
		class="sticky top-0 z-30 -mx-4 -mt-4 flex flex-wrap items-center justify-between gap-4 border-b border-(--border) bg-(--bg) px-4 pt-4 pb-4"
	>
		<div class="flex min-w-0 items-center gap-4">
			{#if hasLogo}
				<img src={siteFileUrl('logo')} alt="" class="h-14 w-auto max-w-40 object-contain" />
			{/if}

			<!-- "FAMILY KIOSK - Location 1": which kiosk, at which centre. -->
			<p class="min-w-0 truncate text-2xl font-extrabold text-(--primary)">
				{#if label}
					<span class="uppercase tracking-wide">{label}</span> -
				{/if}
				{centreName}
			</p>
		</div>

		<div class="flex flex-wrap items-center gap-6">
			{#if actions}
				<div class="flex flex-wrap items-center gap-3">
					{@render actions()}
				</div>
			{/if}

			<KioskClock />
		</div>
	</header>

	<div class="flex flex-1 flex-col">
		{@render children()}
	</div>
</div>
