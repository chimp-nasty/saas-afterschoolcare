<!--
    The header on the platform's own site (its home page, registration, the
    console and its login): the site header (Header) with the platform's
    name, since there's no business here. Every page has a header.
-->
<script lang="ts">
	import Header, { type HeaderLink, type HeaderMenuItem } from '$lib/components/layout/tenant/Header.svelte';

	import { PLATFORM_NAME } from '$lib/platform/site';

	let {
		links = [],
		menuLead = [],
		note,
		onMenu
	}: {
		links?: HeaderLink[];
		// The phone menu's first rows (e.g. Log in).
		menuLead?: HeaderMenuItem[];
		note?: string | null;
		// The console's sidebar drawer, on a phone.
		onMenu?: () => void;
	} = $props();
</script>

<Header homeHref="/" title={PLATFORM_NAME} hasLogo={false} {links} {menuLead} {note} {onMenu} />
