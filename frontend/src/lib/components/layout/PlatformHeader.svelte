<!--
    The header on the platform's own site (its home page, registration, the
    console and its login): the site header (Header) with the platform's
    name (its uploaded logo, a wordmark, when it has one), since there's no
    business here. Its admins also get a Platform link to the console.
    Every page has a header.
-->
<script lang="ts">
	import Header, {
		type HeaderLink,
		type HeaderMenuItem,
		type HeaderMenuSection
	} from '$lib/components/layout/tenant/Header.svelte';

	import { page } from '$app/state';

	import { platformFileUrl } from '$lib/api/platform/adapters/platformSite';
	import { PLATFORM_CONSOLE_LINK, PLATFORM_NAME } from '$lib/platform/site';

	let {
		links = [],
		menuLead = [],
		note,
		menuSections
	}: {
		links?: HeaderLink[];
		// The phone menu's first rows (e.g. Log in).
		menuLead?: HeaderMenuItem[];
		note?: string | null;
		// The console's sidebar links, in the drawer on a phone.
		menuSections?: HeaderMenuSection[];
	} = $props();

	// The platform's branding and whether its admin is logged in, loaded
	// for every page of its site (routes/+layout.ts).
	const hasLogo = $derived(Boolean(page.data.platformSite?.has_logo));

	// Its admins get the console beside the site's links.
	const shownLinks = $derived(
		page.data.isPlatformAdmin && links.length > 0 ? [...links, PLATFORM_CONSOLE_LINK] : links
	);
</script>

<Header
	homeHref="/"
	title={PLATFORM_NAME}
	hasLogo={hasLogo}
	logoSrc={platformFileUrl('logo')}
	logoIsName
	links={shownLinks}
	{menuLead}
	{note}
	{menuSections}
/>
