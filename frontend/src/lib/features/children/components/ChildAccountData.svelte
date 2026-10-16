<script lang="ts">
	import type { ChildTableResponse } from "$lib/api/schema";
    import Card from "$lib/components/layout/Card.svelte";
    import DataCard from "$lib/components/layout/DataCard.svelte";
    import Button from "$lib/components/actions/Button.svelte";
	import { goto } from "$app/navigation";

    let { 
        childProfiles,
        locationCode
    }: { 
        childProfiles: ChildTableResponse[],
        locationCode: string
    } = $props();
</script>

<Card >
    <div class="flex flex-col gap-4">
        {#each childProfiles as child}
            <DataCard
                title={`${child.first_name} ${child.last_name}`}
                href={`/${locationCode}/account/children/${child.id}`}
                data={[
                    {
                        label: "Review Status",
                        value: child.review_status,
                        format: 'enum'
                    },
                    {
                        label: "Date of Birth",
                        value: child.dob,
                        format: 'date'
                    },
                ]}
            />
        {/each}

        <Button
            fullWidth
            onclick={() => goto(`/${locationCode}/account/children/new`)}
        >
            Add New
        </Button>
    </div>
</Card>