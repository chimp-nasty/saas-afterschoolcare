import { createKioskDevicesApi } from '$lib/api/public/adapters/kioskDevices';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch
}) => {
	depends('app:kiosk-devices');

	const api = createKioskDevicesApi(fetch);
	const [devicesResponse, settingsResponse] = await Promise.all([api.list(), api.settings()]);

	return {
		devices: devicesResponse.data ?? [],
		settings: settingsResponse.data
	};
};
