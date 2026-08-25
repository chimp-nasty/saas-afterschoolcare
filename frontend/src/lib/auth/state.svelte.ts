import { writable } from 'svelte/store';


export type AuthState = {
	authenticated: boolean;
	userId: string | null;
	tenantId: string | null;
	email: string | null;
	firstName: string | null;
	roles: string[];
};


function emptyAuthState(): AuthState {
	return {
		authenticated: false,
		userId: null,
		tenantId: null,
		email: null,
		firstName: null,
		roles: []
	};
}


export const auth = writable<AuthState>(
	emptyAuthState()
);


export function setSession(
	session: Omit<AuthState, 'authenticated'>
): void {
	auth.set({
		authenticated: true,
		...session
	});
}


export function clearSession(): void {
	auth.set(
		emptyAuthState()
	);
}