<!--
    /{location}/programs (docs/public-site.md, section 4): each service the
    centre offers, in full: ages, times and price, then its description,
    what's included, drop-off and pickup, what to bring and activities. Each
    has its own anchor (its id) for links from the centre page and
    /locations. A superadmin here edits each program's text in place, on
    desktop (EditableSection; the API checks it).
-->
<script lang="ts">
	import { goto, invalidate } from '$app/navigation';

	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import EditableSection from '$lib/components/layout/EditableSection.svelte';
	import SiteSection from '$lib/components/layout/SiteSection.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Program from '$lib/features/services/components/Program.svelte';
	import ProgramForm from '$lib/features/services/components/ProgramForm.svelte';

	import { auth } from '$lib/auth/state.svelte';
	import { createLocationServicesApi } from '$lib/api/public/adapters/location-services';
	import type { UpdateLocationServiceConfigRequest } from '$lib/api/schema';

	let { data } = $props();

	const servicesApi = createLocationServicesApi();

	const name = $derived(data.location.location_name);

	// The program's text is the centre's: its superadmins (the owner is one
	// at every centre), logged in here.
	const canEdit = $derived($auth.authenticated && $auth.roles.includes('superadmin'));

	const isFamily = $derived($auth.authenticated && $auth.roles.includes('customer'));

	const mainAction = $derived(
		isFamily
			? { label: 'Book a session', href: `/${data.locationCode}/bookings/new` }
			: { label: 'Enrol now', href: `/${data.locationCode}/register` }
	);

	async function save(id: string, body: UpdateLocationServiceConfigRequest, done: () => void) {
		const response = await servicesApi.updateConfig(id, body);

		if (response.ok) {
			await invalidate('app:programs');
			done();
		}

		return response;
	}
</script>

<SiteSection>
	<div class="flex max-w-3xl flex-col gap-5 py-4 md:py-8">
		<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>

		<p class="label-text">{name}</p>

		<h1 class="display-text">Our programs</h1>

		<p class="text-base text-(--text-muted) md:text-lg">
			What each program includes, how drop-off and pickup work, and what to bring.
		</p>

		{#if data.services.length > 1}
			<nav class="flex flex-wrap gap-x-6 gap-y-2" aria-label="Programs">
				{#each data.services as service (service.id)}
					<a
						href={`#${service.id}`}
						class="flex min-h-11 items-center text-base font-semibold text-(--primary) hover:text-(--primary-hover)"
					>
						{service.service_name}
					</a>
				{/each}
			</nav>
		{/if}
	</div>
</SiteSection>

{#each data.services as service, index (service.id)}
	<SiteSection id={service.id} tone={index % 2 === 0 ? 'muted' : 'plain'}>
		<EditableSection {canEdit} label={`the ${service.service_name} program`}>
			<div class="pr-14">
				<Program {service} />
			</div>

			{#snippet editor(done)}
				<ProgramForm {service} onsubmit={(body) => save(service.id, body, done)} oncancel={done} />
			{/snippet}
		</EditableSection>
	</SiteSection>
{:else}
	<SiteSection tone="muted">
		<EmptyState message="Programs will be listed here soon." />
	</SiteSection>
{/each}

{#if data.services.length > 0 && !(($auth.authenticated && !isFamily) || data.signedInElsewhere)}
	<SiteSection tone="tint">
		<div class="flex flex-col gap-5">
			<h2 class="headline-text">Ready to start?</h2>

			<ActionBar start>
				<Button variant="ghost" onclick={() => goto(`/${data.locationCode}`)}>Back to {name}</Button>
				<Button onclick={() => goto(mainAction.href)}>{mainAction.label}</Button>
			</ActionBar>
		</div>
	</SiteSection>
{/if}
