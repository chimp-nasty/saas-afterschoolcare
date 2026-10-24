import { writable } from 'svelte/store';

export type AuthState = {
	authenticated: boolean;
	initialized: boolean;
	userId: string | null;
	email: string | null;
	firstName: string | null;
	roles: string[];
	// What they may do across the whole business ({resource: actions}): the
	// owner's, which shows "Business settings"; empty for everyone else.
	tenantPermissions: Record<string, string[]>;
};

function emptyAuthState(): AuthState {
	return {
		authenticated: false,
		initialized: false,
		userId: null,
		email: null,
		firstName: null,
		roles: [],
		tenantPermissions: {}
	};
}

export const auth = writable<AuthState>(emptyAuthState());

export function setSession(
	session: Omit<AuthState, 'authenticated' | 'initialized'>
): void {
	auth.set({
		authenticated: true,
		initialized: true,
		...session
	});
}

export function clearSession(): void {
	auth.set({
		...emptyAuthState(),
		initialized: true
	});
}