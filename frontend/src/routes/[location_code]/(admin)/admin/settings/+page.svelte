<!--
    Admin › Service settings: each service the location has, offered or not,
    with its price, session times, description and policies. One card per
    service, saved on its own.
-->
<script lang="ts">
    import { invalidate } from "$app/navigation";

    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import ServiceSettingsForm from "$lib/features/services/components/ServiceSettingsForm.svelte";

    import { createLocationServicesApi } from "$lib/api/public/adapters/location-services";
    import type { UpdateLocationServiceConfigRequest } from "$lib/api/schema";
    import { formatTimestamp } from "$lib/utils/helpers";

    let { data } = $props();

    const servicesApi = createLocationServicesApi();

    async function save(id: string, body: UpdateLocationServiceConfigRequest) {
        const response = await servicesApi.updateConfig(id, body);

        if (response.ok) {
            await invalidate("app:service-settings");
        }

        return response;
    }
</script>

<Page width="wide">
    <PageHeader
        title="Service settings"
        description="What each service costs, when it runs and its policies. Families only see services that are offered."
    />

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {#each data.services as service (service.id)}
            <section class="flex flex-col gap-3">
                <div class="flex flex-wrap items-baseline justify-between gap-2">
                    <h2 class="text-lg font-extrabold text-(--text)">{service.service_name}</h2>
                    <p class="text-sm text-(--text-muted)">
                        {service.is_active ? "Offered" : "Not offered"} · last changed {formatTimestamp(service.updated_at)}
                    </p>
                </div>

                <ServiceSettingsForm {service} onsubmit={(body) => save(service.id, body)} />
            </section>
        {:else}
            <p class="text-base text-(--text-muted)">This location has no services.</p>
        {/each}
    </div>
</Page>
