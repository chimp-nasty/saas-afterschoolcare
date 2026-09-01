<script lang="ts">
    import { auth } from "$lib/auth/state.svelte";
</script>

<p>welcome home, {$auth.roles[0]}</p>