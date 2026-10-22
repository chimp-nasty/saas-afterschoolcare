<script lang="ts">
	import './layout.css';

	import { Toaster } from 'svelte-sonner';

	let { children } = $props();
</script>

<!-- Every page's toasts, including the tenant landing page and error pages. -->
<Toaster
	position="top-center"
	duration={3000}
	toastOptions={{
		classes: {
			toast: 'rounded-2xl! border! border-(--border)! text-sm! font-extrabold!',
			success: 'bg-(--success-soft)! text-(--success-text)!',
			error: 'bg-(--danger-soft)! text-(--danger-text)!'
		}
	}}
/>

{@render children()}
