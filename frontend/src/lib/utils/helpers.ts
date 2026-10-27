export function formatDateDDMMYYYY(value: string): string {
    const [year, month, day] = value.slice(0, 10).split('-');

    return `${day}/${month}/${year}`;
}

export function formatTimestampDDMMYYYY(value: string): string {
    return new Date(value).toLocaleString('en-AU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Customer-facing dates and money (see "Words and formats" in CLAUDE.md).

// "Tue, 20 Oct", plus the year when it isn't this year ("Mon, 20 Oct 2025").
function formatWeekdayDate(date: Date): string {
    return date.toLocaleDateString('en-AU', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        year: date.getFullYear() === new Date().getFullYear() ? undefined : 'numeric'
    });
}

// A YYYY-MM-DD date, read as a local date so it can't shift a day.
export function formatDate(value: string): string {
    return formatWeekdayDate(new Date(`${value.slice(0, 10)}T00:00:00`));
}

// "Tue, 20 Oct – Fri, 24 Oct"; a single date when both ends are the same day.
export function formatDateRange(first: string, last: string): string {
    return first === last
        ? formatDate(first)
        : `${formatDate(first)} – ${formatDate(last)}`;
}

// An ISO timestamp, as the date it falls on in the viewer's timezone.
export function formatTimestamp(value: string): string {
    return formatWeekdayDate(new Date(value));
}

// "1 Mar 2019": a date of birth reads oddly with a weekday.
export function formatDateOfBirth(value: string): string {
    return new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString('en-AU', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
    });
}

// "3:00pm" for a time of day ("15:00:00"), as sent by the API in the
// location's timezone. Times are shown as given, never converted.
export function formatTime(value: string): string {
    const [hours, minutes] = value.split(':').map(Number);
    const suffix = hours < 12 ? 'am' : 'pm';
    const hour = hours % 12 === 0 ? 12 : hours % 12;

    return `${hour}:${String(minutes).padStart(2, '0')}${suffix}`;
}

// "3:00pm – 6:00pm"
// Weekdays (ISO: 1 Monday to 7 Sunday) as families read them: runs of
// three or more collapse ("Mon–Fri"), the rest are listed ("Mon, Wed, Fri";
// "Sat, Sun").
export function formatWeekdays(days: number[]): string {
	const names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
	const sorted = [...new Set(days)].filter((day) => day >= 1 && day <= 7).sort((a, b) => a - b);
	const parts: string[] = [];

	for (let index = 0; index < sorted.length; ) {
		let end = index;

		while (end + 1 < sorted.length && sorted[end + 1] === sorted[end] + 1) end++;

		if (end - index >= 2) {
			parts.push(`${names[sorted[index] - 1]}–${names[sorted[end] - 1]}`);
		} else {
			for (let day = index; day <= end; day++) parts.push(names[sorted[day] - 1]);
		}

		index = end + 1;
	}

	return parts.join(', ');
}

export function formatTimeRange(start: string, end: string): string {
    return `${formatTime(start)} – ${formatTime(end)}`;
}

// "0400 000 000" for a mobile, "(07) 3000 0000" for a landline. Phones are
// stored as 10 digits.
export function formatPhone(value: string): string {
    if (!/^\d{10}$/.test(value)) {
        return value;
    }

    return value.startsWith('04')
        ? `${value.slice(0, 4)} ${value.slice(4, 7)} ${value.slice(7)}`
        : `(${value.slice(0, 2)}) ${value.slice(2, 6)} ${value.slice(6)}`;
}

// "$30.00"
export function formatMoney(cents: number, currency: string): string {
    return new Intl.NumberFormat('en-AU', {
        style: 'currency',
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(cents / 100);
}

export function formatEnum(value: string): string {
	return value
		.replaceAll('_', ' ')
		.toLowerCase()
		.replace(/\b\w/g, (char) => char.toUpperCase());
}