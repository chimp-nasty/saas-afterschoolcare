import { toast } from 'svelte-sonner';


export type ApiResponse<T = unknown> = {
	ok: boolean;
	msg: string;
	data: T | null;
	status: number;
	fieldErrors: Record<string, string>;
};

type FieldError = {
	field: string;
	message: string;
};

type ApiBody =
	| Record<string, unknown>
	| URLSearchParams
	| FormData
	| string
	| undefined;

type ApiWrapperOptions = {
	method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
	body?: ApiBody;
	headers?: Record<string, string>;
	onSuccess?: () => void | Promise<void>;
	fetcher?: typeof fetch;
	// No success toast, for a step inside a longer action (e.g. starting an
	// upload); errors still toast.
	quiet?: boolean;
	// No toasts at all: the caller shows the outcome itself (the kiosk
	// shows messages large on screen).
	silent?: boolean;
};

// The backend returns 422s as { data: [{ field, message }] }; key them by field.
function toFieldErrors(data: unknown): Record<string, string> {
	if (!Array.isArray(data)) return {};

	const errors: Record<string, string> = {};

	for (const error of data as FieldError[]) {
		if (error.field && !errors[error.field]) {
			errors[error.field] = error.message;
		}
	}

	return errors;
}


export async function apiWrapper<T>(
	url: string,
	options: ApiWrapperOptions = {}
): Promise<ApiResponse<T>> {
	const {
		method = 'GET',
		body,
		headers = {},
		onSuccess,
		fetcher = fetch,
		quiet = false,
		silent = false
	} = options;

	function finalizeResponse(
		response: ApiResponse<T>
	): ApiResponse<T> {
		if (method !== 'GET' && !silent) {
			if (response.ok) {
				if (quiet) return response;

				toast.success(response.msg);
			} else {
				toast.error(response.msg);
			}
		}

		return response;
	}

	try {
		const isFormData = body instanceof FormData;
		const isUrlEncoded = body instanceof URLSearchParams;
		const isStringBody = typeof body === 'string';

		const isJsonBody =
			body !== undefined &&
			!isFormData &&
			!isUrlEncoded &&
			!isStringBody;

		const finalHeaders: Record<string, string> = {
			...headers
		};

		if (isJsonBody && !finalHeaders['Content-Type']) {
			finalHeaders['Content-Type'] = 'application/json';
		}

		if (isUrlEncoded && !finalHeaders['Content-Type']) {
			finalHeaders['Content-Type'] =
				'application/x-www-form-urlencoded';
		}

		const response = await fetcher(url, {
			method,
			headers: finalHeaders,
			credentials: 'include',
			body:
				body === undefined
					? undefined
					: isJsonBody
						? JSON.stringify(body)
						: body
		});

		const status = response.status;
		const contentType =
			response.headers.get('content-type') ?? '';

		if (!contentType.includes('application/json')) {
			return finalizeResponse({
				ok: response.ok,
				msg: response.ok
					? 'Success'
					: 'Something went wrong',
				data: null,
				status,
				fieldErrors: {}
			});
		}

		const result = (
			await response.json()
		) as { ok: boolean; msg: string; data?: unknown };

		const isValidationError = status === 422;

		const apiResponse: ApiResponse<T> = {
			ok: result.ok,
			msg: result.msg,
			data: isValidationError
				? null
				: ((result.data ?? null) as T | null),
			status,
			fieldErrors: isValidationError
				? toFieldErrors(result.data)
				: {}
		};

		if (apiResponse.ok && onSuccess) {
			await onSuccess();
		}

		return finalizeResponse(apiResponse);

	} catch (error) {
		console.error('API wrapper error', {
			url,
			method,
			error
		});

		return finalizeResponse({
			ok: false,
			msg: 'Network error',
			data: null,
			status: 0,
			fieldErrors: {}
		});
	}
}