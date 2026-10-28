// "You have new messages" once per login: the login page leaves a mark,
// and the customer home shows the pop-up (NewMessagesModal) and clears it.
// Browser storage can be missing or blocked (private windows); then there's
// simply no pop-up.
const KEY = 'show-new-messages';

export function markJustLoggedIn(): void {
	try {
		sessionStorage.setItem(KEY, '1');
	} catch {
		// No storage: no pop-up.
	}
}

// True once, straight after logging in.
export function takeJustLoggedIn(): boolean {
	try {
		const marked = sessionStorage.getItem(KEY) === '1';
		sessionStorage.removeItem(KEY);

		return marked;
	} catch {
		return false;
	}
}
