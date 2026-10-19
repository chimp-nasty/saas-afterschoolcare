import { goto, invalidate } from '$app/navigation';

import { createAuthApi } from '$lib/api/auth/adapters/auth';
import { clearSession } from '$lib/auth/state.svelte';

// Shared by the sidebar (staff, admin, desktop) and the account page
// (customers on mobile, who have no sidebar).
export async function logout(locationCode: string): Promise<void> {
	await createAuthApi().logout();

	clearSession();

	// Reload the layout's session too. Otherwise its data still holds the
	// old one, and the layout puts it back into the auth store on the next
	// navigation (so the app thinks you're still logged in).
	await invalidate('app:session');

	await goto(`/${locationCode}/`);
}
