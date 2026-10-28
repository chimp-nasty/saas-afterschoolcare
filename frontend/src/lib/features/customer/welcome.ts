// The welcome pop-up on /setup, once, straight after registering: the
// register page leaves a mark and setup's WelcomeModal clears it. Browser
// storage can be missing or blocked (private windows); then there's simply
// no pop-up.
const KEY = 'show-setup-welcome';

export function markJustRegistered(): void {
	try {
		sessionStorage.setItem(KEY, '1');
	} catch {
		// No storage: no pop-up.
	}
}

// True once, straight after registering.
export function takeJustRegistered(): boolean {
	try {
		const marked = sessionStorage.getItem(KEY) === '1';
		sessionStorage.removeItem(KEY);

		return marked;
	} catch {
		return false;
	}
}
