import { PUBLIC_PLATFORM_HOST } from '$env/static/public';

// The platform's name, in its own site's header (businesses' sites show
// theirs instead).
export const PLATFORM_NAME = 'Session Pilot';

// The platform's own site (the bare base domain, host and port): the
// platform console and registration live there, never on a tenant's site,
// and its home page isn't a tenant's landing page.
export function isPlatformSite(url: URL): boolean {
	return url.host.toLowerCase() === PUBLIC_PLATFORM_HOST.toLowerCase();
}
