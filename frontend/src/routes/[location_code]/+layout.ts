export function load({ params }) {
	if (!params.location_code) {
		throw new Error(
			'Location code is required'
		);
	}

	return {
		locationCode: params.location_code
	};
}