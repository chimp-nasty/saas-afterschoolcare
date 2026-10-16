import type { ApiResponse } from '$lib/api/wrapper';

export type FormErrors<T> = Partial<
	Record<keyof T, string>
>;

// Pages pass this to forms: the page calls the API, the form handles
// loading, field errors and reset from the response it gets back.
export type SubmitHandler<T> = (
	body: T
) => Promise<ApiResponse<unknown>>;
