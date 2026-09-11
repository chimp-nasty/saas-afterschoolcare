export function formatDateDDMMYYYY(value: string): string {
    const [year, month, day] = value.slice(0, 10).split('-');

    return `${day}/${month}/${year}`;
}

export function formatTimestampDDMMYYYY(value: Date): string {
    return value.toLocaleString('en-AU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

export function formatEnum(value: string): string {
	return value
		.replaceAll('_', ' ')
		.toLowerCase()
		.replace(/\b\w/g, (char) => char.toUpperCase());
}