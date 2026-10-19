import { goto } from '$app/navigation';

import { createAuthApi } from '$lib/api/auth/adapters/auth';
import { clearSession } from '$lib/auth/state.svelte';

// Shared by the sidebar (staff, admin, desktop) and the account page
// (customers on mobile, who have no sidebar).
export async function logout(locationCode: string): Promise<void> {
	await createAuthApi().logout();

	clearSession();

	await goto(`/${locationCode}/`);
}
