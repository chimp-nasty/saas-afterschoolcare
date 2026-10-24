import { goto, invalidate } from '$app/navigation';

import { createAuthApi } from '$lib/api/auth/adapters/auth';

// "Manage centre": switch the login to that centre (the owner is
// superadmin at every one) and open it, without logging in again.
export async function manageCentre(locationCode: string): Promise<void> {
	const response = await createAuthApi().switchLocation(locationCode);

	if (response.ok) {
		await invalidate('app:session');
		await goto(`/${locationCode}/home`);
	}
}
