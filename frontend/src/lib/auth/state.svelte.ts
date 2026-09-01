import { writable } from 'svelte/store';

export type AuthState = {
	authenticated: boolean;
	initialized: boolean;
	userId: string | null;
	locationId: string | null;
	email: string | null;
	firstName: string | null;
	roles: string[];
};

function emptyAuthState(): AuthState {
	return {
		authenticated: false,
		initialized: false,
		userId: null,
		locationId: null,
		email: null,
		firstName: null,
		roles: []
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