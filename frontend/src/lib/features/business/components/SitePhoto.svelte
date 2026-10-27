<!--
    A photo on the public site (docs/public-site.md, stage 9): the
    business's, a centre's or a program's, filling its space, centred, with
    its description for screen readers (decorative without one).
-->
<script lang="ts">
	let {
		src,
		alt
	}: {
		// Its link, with its version (the adapters' photo URLs).
		src: string;
		alt: string | null;
	} = $props();
</script>

<img
	{src}
	alt={alt ?? ''}
	class="aspect-[4/3] w-full rounded-2xl bg-(--surface-muted) object-cover"
	loading="lazy"
/>
