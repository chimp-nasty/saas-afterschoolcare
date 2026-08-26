export function createFormState<T extends object>(
	initialState: T
): T {
	return structuredClone(initialState);
}