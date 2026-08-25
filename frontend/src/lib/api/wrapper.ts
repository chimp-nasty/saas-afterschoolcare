export type ApiResponse<T = unknown> = {
	ok: boolean;
	msg: string;
	data: T | null;
	status: number;
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
};

export async function apiWrapper<T = unknown>(
	url: string,
	options: ApiWrapperOptions = {}
): Promise<ApiResponse<T>> {
	const {
		method = 'GET',
		body,
		headers = {},
		onSuccess,
		fetcher = fetch
	} = options;

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
			finalHeaders['Content-Type'] = 'application/x-www-form-urlencoded';
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
		const contentType = response.headers.get('content-type') ?? '';

		if (!contentType.includes('application/json')) {
			return {
				ok: response.ok,
				msg: response.ok ? 'Success' : 'Something went wrong',
				data: null,
				status
			};
		}

		const result = (await response.json()) as Omit<ApiResponse<T>, 'status'>;

		const apiResponse: ApiResponse<T> = {
			ok: result.ok,
			msg: result.msg,
			data: result.data ?? null,
			status
		};

		if (apiResponse.ok && onSuccess) {
			await onSuccess();
		}

		return apiResponse;
	} catch {
		return {
			ok: false,
			msg: 'Network error',
			data: null,
			status: 0
		};
	}
}