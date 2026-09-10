<script lang="ts">
	import type { ChildTableResponse } from "$lib/api/public/types/children";
    import Card from "$lib/components/layout/Card.svelte";
    import DataCard from "$lib/components/layout/DataCard.svelte";

    let { childProfiles }: { childProfiles: ChildTableResponse[] } = $props();
</script>

<Card >
    <div class="flex flex-col gap-4">
        {#each childProfiles as child}
            <DataCard
                title={`${child.first_name} ${child.last_name}`}

                data={[
                    {
                        label: "Review Status",
                        value: child.review_status
                    },
                    {
                        label: "Date of Birth",
                        value: child.dob
                    },
                ]}
            />
        {/each}
    </div>
</Card>