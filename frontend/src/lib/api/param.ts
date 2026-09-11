type QueryParamValue =
    | string
    | number
    | boolean
    | null
    | undefined;

type QueryParam =
    | QueryParamValue
    | QueryParamValue[];

export function buildQueryParams(
    ...sources: Record<string, QueryParam>[]
): string {
    const params = new URLSearchParams();

    for (const source of sources) {
        for (const [key, value] of Object.entries(source)) {
            if (value === undefined || value === null) {
                continue;
            }

            if (Array.isArray(value)) {
                for (const item of value) {
                    if (item !== undefined && item !== null) {
                        params.append(key, String(item));
                    }
                }

                continue;
            }

            params.set(key, String(value));
        }
    }

    return params.toString();
}