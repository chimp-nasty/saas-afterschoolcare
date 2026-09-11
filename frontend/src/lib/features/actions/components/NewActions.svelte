<script lang="ts">
    import type { ActionResponse } from "$lib/api/public/types/actions";

    import Card from "$lib/components/layout/Card.svelte";
    import DataCard from "$lib/components/layout/DataCard.svelte";

    import { buildActionHref } from "$lib/navigation/action-navigation";

    let {
        actions,
        locationCode
    }: {
        actions: ActionResponse[];
        locationCode: string;
    } = $props();
</script>

<Card>
    <div class="flex flex-col gap-4">
        {#each actions as action}
            <DataCard
                title={action.title}
                href={buildActionHref(
                    locationCode,
                    {
                        childId: action.child_id,
                        target: action.target
                    }
                ) ?? undefined}
                data={[
                    {
                        label: "Message",
                        value: action.message
                    },
                    {
                        label: "Created",
                        value: action.created_at
                    },
                ]}
            />
        {/each}
    </div>
</Card>