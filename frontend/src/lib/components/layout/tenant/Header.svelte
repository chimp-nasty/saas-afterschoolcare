<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import { Bell, Menu } from 'lucide-svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import { auth } from '$lib/auth/state.svelte';

	let {
		onMenu
	}: {
		onMenu?: () => void;
	} = $props();
</script>

<header
	class="
		sticky
		top-0
		z-40
		mb-6
		w-full
		border-b
		border-(--border)
		bg-(--surface)/90
		p-4
		backdrop-blur-md
	"
>
	<div class="flex min-h-12 w-full items-center gap-4">
		<p class="mr-auto text-sm font-semibold text-(--text)">
			{page.data.location.tenant_name} - {page.data.location.location_code}
		</p>

		{#if $auth.authenticated}
			<p class="hidden text-sm text-(--text-muted) md:block">
				Logged in as {$auth.firstName ?? $auth.email}
			</p>

			<Button
				variant="ghost"
				class="group"
			>
				<span
					class="
						inline-flex
						origin-top
						group-hover:animate-[bell-ring_0.5s_ease-in-out]
					"
				>
					<Bell size={20} />
				</span>
			</Button>

			<div class="md:hidden">
				<Button
					variant="ghost"
					onclick={onMenu}
				>
					<Menu size={20} />
				</Button>
			</div>
		{:else}
			<Button
				variant="ghost"
				onclick={() => goto(`/${page.params.location_code}/login`)}
			>
				Login
			</Button>
		{/if}
	</div>
</header>