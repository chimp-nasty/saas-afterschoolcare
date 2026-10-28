<!--
    A photo on the public site (docs/public-site.md, stage 9): the
    business's, a centre's or a program's, filling its space, centred, with
    its description for screen readers (decorative without one).

    `wave` (the platform's hero, docs/platform-site.md): from lg its left
    edge is cut in a sweeping curve, with a soft echo of the curve behind
    it in the main colour. On a phone it's the usual rounded photo.
-->
<script lang="ts">
	let {
		src,
		alt,
		shape = 'rounded'
	}: {
		// Its link, with its version (the adapters' photo URLs).
		src: string;
		alt: string | null;
		shape?: 'rounded' | 'wave';
	} = $props();

	// The curve, in the photo's own box (0 to 1 each way): in from the
	// bottom left, sweeping up to the top left, rounded on the right.
	const WAVE =
		'M0.3,1 C0.14,0.86 0.24,0.6 0.1,0.4 C0.03,0.3 0,0.16 0,0 L0.97,0 Q1,0 1,0.04 L1,0.96 Q1,1 0.97,1 Z';
</script>

{#if shape === 'wave'}
	<div class="relative">
		<!-- The curve itself, used by both layers below. -->
		<svg class="absolute size-0" aria-hidden="true">
			<defs>
				<clipPath id="site-photo-wave" clipPathUnits="objectBoundingBox">
					<path d={WAVE} />
				</clipPath>
			</defs>
		</svg>

		<!-- The echo: the same curve a little to the left, decoration only. -->
		<div
			class="absolute inset-0 hidden -translate-x-8 bg-(--primary-soft) [clip-path:url(#site-photo-wave)] lg:block"
			aria-hidden="true"
		></div>

		<img
			{src}
			alt={alt ?? ''}
			class="relative aspect-[4/3] w-full rounded-2xl bg-(--surface-muted) object-cover lg:aspect-[5/4] lg:rounded-none lg:[clip-path:url(#site-photo-wave)]"
			loading="lazy"
		/>
	</div>
{:else}
	<img
		{src}
		alt={alt ?? ''}
		class="aspect-[4/3] w-full rounded-2xl bg-(--surface-muted) object-cover"
		loading="lazy"
	/>
{/if}
