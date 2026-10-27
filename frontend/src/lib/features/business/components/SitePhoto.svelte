<!--
    One of the business's photos on its public pages (docs/public-site.md,
    stage 9): filling its space, centred, with the owner's description for
    screen readers (decorative without one).
-->
<script lang="ts">
	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import type { PhotoResponse } from '$lib/api/schema';

	let {
		kind,
		photo
	}: {
		kind: 'hero_photo' | 'about_photo';
		photo: PhotoResponse;
	} = $props();
</script>

<img
	src={siteFileUrl(kind, photo.version)}
	alt={photo.alt ?? ''}
	class="aspect-[4/3] w-full rounded-2xl bg-(--surface-muted) object-cover"
	loading="lazy"
/>
