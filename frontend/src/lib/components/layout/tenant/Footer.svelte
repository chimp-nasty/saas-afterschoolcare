<script lang="ts">
	import { page } from "$app/state";
</script>

<div class="flex flex-row gap-4 self-center text-(--text) text-sm p-4 items-center justify-center">
	<div>
		© {new Date().getFullYear()} {page.data.location.tenant_name}. All rights reserved.
	</div>
</div>