<script lang="ts">
	import Layout from '$lib/components/layout/Layout.svelte';
	import Header from '$lib/components/layout/Header.svelte';
	import Footer from '$lib/components/layout/Footer.svelte';

    import Sidebar, { type SidebarItem} from '$lib/components/controls/Sidebar.svelte';

	let { children } = $props();

	const items: SidebarItem[] = [
        {
            label: "Home",
            href: "/home"
        }
    ]
</script>

<Layout>
	{#snippet header()}
		<Header />
	{/snippet}

	{#snippet sidebar()}
		<Sidebar {items} />
	{/snippet}

	{@render children()}

	{#snippet footer()}
		<Footer />
	{/snippet}
</Layout>