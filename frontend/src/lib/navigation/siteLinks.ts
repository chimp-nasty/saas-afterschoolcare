// The public site header's shared links (docs/public-site.md, section 2).
// Programs belongs to a centre, so each centre's layout makes its own.
import type { HeaderLink } from '$lib/components/layout/tenant/Header.svelte';

export const LOCATIONS_LINK: HeaderLink = { label: 'Locations', href: '/locations' };
export const ABOUT_LINK: HeaderLink = { label: 'About', href: '/about' };

// Business settings, for its owner only (beside About).
export const BUSINESS_LINK: HeaderLink = { label: 'Business', href: '/business' };

// The header inside Business settings: only the owner gets there.
export const BUSINESS_HEADER_LINKS: HeaderLink[] = [LOCATIONS_LINK, ABOUT_LINK, BUSINESS_LINK];

/**
 * Whether the session holds the business's own permissions (its owner),
 * from the session's tenant permissions. Only decides whether the Business
 * link shows: /business and its API refuse anyone else themselves.
 */
export function isBusinessOwner(tenantPermissions: Record<string, string[]> | null | undefined): boolean {
	return Object.keys(tenantPermissions ?? {}).length > 0;
}
