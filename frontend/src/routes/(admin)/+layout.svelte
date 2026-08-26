<script lang="ts">
    import Authorize from '$lib/auth/Authorize.svelte';
	import Layout from '$lib/components/layout/Layout.svelte';

	import Header from '$lib/components/layout/Header.svelte';
	import Footer from '$lib/components/layout/Footer.svelte';
    import Sidebar, { type SidebarItem} from '$lib/components/controls/Sidebar.svelte';

	let { children } = $props();

    const roles = ["admin"]

    const items: SidebarItem[] = [
    ]
</script>

<Authorize {roles}>
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
</Authorize>