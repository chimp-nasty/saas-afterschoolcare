export function formatDateDDMMYYYY(value: string): string {
	const [year, month, day] = value.split('-');

	return `${day}/${month}/${year}`;
}

export function formatEnum(value: string): string {
	return value
		.replaceAll('_', ' ')
		.toLowerCase()
		.replace(/\b\w/g, (char) => char.toUpperCase());
}