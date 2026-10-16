<script lang="ts">
    import ChildProfileForm from "$lib/features/children/components/ChildProfileForm.svelte";

    import { createChildrenApi } from "$lib/api/public/adapters/children";

    const childApi = createChildrenApi();
</script>

<ChildProfileForm onsubmit={(body) => childApi.create(body)} />
