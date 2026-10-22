<script lang="ts">
	import type { ChildTableResponse } from "$lib/api/schema";
    import DataCard from "$lib/components/layout/DataCard.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import EmptyState from "$lib/components/text/EmptyState.svelte";
	import { goto } from "$app/navigation";

    import { REVIEW_STATUS_LABELS } from "$lib/features/children/review";
    import { formatDateOfBirth } from "$lib/utils/helpers";

    let { 
        childProfiles,
        locationCode
    }: { 
        childProfiles: ChildTableResponse[],
        locationCode: string
    } = $props();
</script>

<div class="flex flex-col gap-4">
    {#each childProfiles as child}
        <DataCard
            title={`${child.first_name} ${child.last_name}`}
            href={`/${locationCode}/account/children/${child.id}`}
            data={[
                {
                    label: "Medical review",
                    value: REVIEW_STATUS_LABELS[child.review_status]
                },
                {
                    label: "Date of birth",
                    value: formatDateOfBirth(child.dob)
                },
            ]}
        />
    {:else}
        <EmptyState message="You haven't added any children yet." />
    {/each}

    <Button
        fullWidth
        onclick={() => goto(`/${locationCode}/account/children/new`)}
    >
        Add a child
    </Button>
</div>