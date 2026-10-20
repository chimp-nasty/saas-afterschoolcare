import { goto } from '$app/navigation';
import { toast } from 'svelte-sonner';

// A page that doesn't exist, at a location that does: home if logged in,
// otherwise the location's landing page. (A location that doesn't exist
// goes to the tenant's page, "/": routes/+error.svelte.)
export async function leaveMissingPage(
	locationCode: string,
	isLoggedIn: boolean
): Promise<void> {
	toast.error("That page doesn't exist, so we've taken you home.");

	await goto(isLoggedIn ? `/${locationCode}/home` : `/${locationCode}`, {
		replaceState: true
	});
}
