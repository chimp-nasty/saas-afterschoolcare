import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	CreateKioskDeviceRequest,
	KioskDeviceResponse,
	KioskSettingsResponse,
	KioskSetupCodeResponse,
	UpdateKioskSettingsRequest
} from '$lib/api/schema';


// The location's two kiosk tablets (admins).
export function createKioskDevicesApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/kiosk-devices/v1`;

	return {
		list() {
			return apiWrapper<KioskDeviceResponse[]>(
				`${baseUrl}/`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		// The location's kiosk rules (e.g. service times for families).
		settings() {
			return apiWrapper<KioskSettingsResponse>(
				`${baseUrl}/settings`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		updateSettings(body: UpdateKioskSettingsRequest) {
			return apiWrapper<KioskSettingsResponse>(
				`${baseUrl}/settings`,
				{
					method: 'PUT',
					body,
					fetcher
				}
			);
		},

		// Returns the setup code, shown once.
		create(body: CreateKioskDeviceRequest) {
			return apiWrapper<KioskSetupCodeResponse>(
				`${baseUrl}/`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		},

		// A new code to pair a (replacement) tablet; the old one stops working.
		newSetupCode(deviceId: string) {
			return apiWrapper<KioskSetupCodeResponse>(
				`${baseUrl}/${deviceId}/setup-code`,
				{
					method: 'POST',
					fetcher
				}
			);
		},

		revoke(deviceId: string) {
			return apiWrapper<KioskDeviceResponse>(
				`${baseUrl}/${deviceId}/revoke`,
				{
					method: 'POST',
					fetcher
				}
			);
		}
	};
}
