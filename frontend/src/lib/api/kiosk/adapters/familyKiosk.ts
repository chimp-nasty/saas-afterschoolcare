import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	KioskInfoResponse,
	KioskLoginResponse,
	KioskSessionResponse,
	KioskSignResponse,
	KioskTodayResponse
} from '$lib/api/schema';

// The kiosk's session token travels in this header (never a cookie).
export const KIOSK_SESSION_HEADER = 'X-Kiosk-Session';

// The family kiosk (and pairing, for both kinds). The tablet is identified
// by its httpOnly device cookie; the person by `token`. Every call is
// silent: the kiosk shows outcomes on screen, not as toasts.
export function createFamilyKioskApi(locationCode: string) {
	const baseUrl = `${API_BASE}/kiosk/v1/${locationCode}`;
	const session = (token: string) => ({ [KIOSK_SESSION_HEADER]: token });

	return {
		pair(code: string) {
			return apiWrapper<KioskInfoResponse>(`${baseUrl}/pair`, {
				method: 'POST',
				body: { code },
				silent: true
			});
		},

		device() {
			return apiWrapper<KioskInfoResponse>(`${baseUrl}/device`, { silent: true });
		},

		login(phone: string, pin: string) {
			return apiWrapper<KioskLoginResponse>(`${baseUrl}/login`, {
				method: 'POST',
				body: { phone, pin },
				silent: true
			});
		},

		changePin(token: string, newPin: string) {
			return apiWrapper<KioskSessionResponse>(`${baseUrl}/pin`, {
				method: 'POST',
				body: { new_pin: newPin },
				headers: session(token),
				silent: true
			});
		},

		forgotPin(phone: string) {
			return apiWrapper<null>(`${baseUrl}/forgot-pin`, {
				method: 'POST',
				body: { phone },
				silent: true
			});
		},

		today(token: string) {
			return apiWrapper<KioskTodayResponse>(`${baseUrl}/today`, {
				headers: session(token),
				silent: true
			});
		},

		sign(token: string, bookingId: string, action: 'in' | 'out') {
			return apiWrapper<KioskSignResponse>(`${baseUrl}/sign`, {
				method: 'POST',
				body: { booking_id: bookingId, action },
				headers: session(token),
				silent: true
			});
		}
	};
}
