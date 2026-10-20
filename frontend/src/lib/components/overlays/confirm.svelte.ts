// Every confirmation in the app goes through confirmAction(): one dialog
// (ConfirmDialog, mounted once in the tenant layout), never window.confirm
// or a hand-built Modal.

export type ConfirmOptions = {
	title: string;
	message: string;
	confirmLabel: string;
	// Defaults to "Keep" for danger confirmations, "Cancel" otherwise.
	cancelLabel?: string;
	// danger: a destructive action (cancel, refund, remove); red confirm button.
	tone?: 'default' | 'danger';
	// Runs after confirming, with a spinner on the confirm button; the dialog
	// closes once it finishes. Do the follow-up (refresh, navigate) in here.
	action?: () => Promise<unknown>;
};

type ConfirmRequest = ConfirmOptions & {
	resolve: (confirmed: boolean) => void;
};

export const confirmState = $state<{ current: ConfirmRequest | null }>({
	current: null
});

// Resolves true once confirmed (and the action, if any, has finished), or
// false for cancel, Escape or tapping outside.
export function confirmAction(options: ConfirmOptions): Promise<boolean> {
	// One at a time: a new request cancels one still showing.
	confirmState.current?.resolve(false);

	return new Promise((resolve) => {
		confirmState.current = { ...options, resolve };
	});
}
