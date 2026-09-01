export type ResponseState = {
	ok: boolean | null;
	message: string | null;
};

export const response = $state<ResponseState>({
	ok: null,
	message: null
});

export function clearResponse() {
	response.ok = null;
	response.message = null;
}

export function setResponse(
	ok: boolean,
	message: string,
	timeout = 2000
) {
	response.ok = ok;
	response.message = message;

	if (timeout > 0) {
		setTimeout(clearResponse, timeout);
	}
}