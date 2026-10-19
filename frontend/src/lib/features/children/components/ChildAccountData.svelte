<script lang="ts">
	import type { ChildTableResponse } from "$lib/api/schema";
    import DataCard from "$lib/components/layout/DataCard.svelte";
    import Button from "$lib/components/actions/Button.svelte";
	import { goto } from "$app/navigation";

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
                    value: child.review_status,
                    format: 'enum'
                },
                {
                    label: "Date of birth",
                    value: formatDateOfBirth(child.dob)
                },
            ]}
        />
    {:else}
        <p class="text-sm text-(--text-muted)">
            You haven't added any children yet.
        </p>
    {/each}

    <Button
        fullWidth
        onclick={() => goto(`/${locationCode}/account/children/new`)}
    >
        Add a child
    </Button>
</div>