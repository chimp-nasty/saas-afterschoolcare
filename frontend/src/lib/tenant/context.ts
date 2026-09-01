export function getTenantCode(): string {
	const hostname = window.location.hostname;
	const tenantCode = hostname.split('.')[0];

	if (!tenantCode) {
		throw new Error('Tenant code is required');
	}

	return tenantCode;
}