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

// The platform's own site's links (its header), and its contact page.
export const PLATFORM_CONTACT_HREF = '/contact';
export const PLATFORM_LINKS = [{ label: 'Contact', href: PLATFORM_CONTACT_HREF }];
// Beside them for the platform's admins, while logged in.
export const PLATFORM_CONSOLE_LINK = { label: 'Platform', href: '/platform' };

// The jnb-digital link on the contact page (docs/platform-site.md): who
// builds the software, for people wanting something like it built.
export const JNB_DIGITAL_URL = 'https://jnb-digital.com.au';

// A page on the platform's own site from anywhere, e.g. a business's site
// linking to the platform's contact page (same protocol as this page).
export function platformUrl(url: URL, path: string): string {
	return `${url.protocol}//${PUBLIC_PLATFORM_HOST}${path}`;
}
