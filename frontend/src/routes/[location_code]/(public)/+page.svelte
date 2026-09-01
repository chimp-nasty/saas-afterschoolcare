<script lang="ts">
	let { data } = $props();
</script>

<h1>
	Welcome to {data.location.display_name ?? data.location.location_name}
</h1>