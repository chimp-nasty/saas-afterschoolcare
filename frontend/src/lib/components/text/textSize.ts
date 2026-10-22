// The two text scales (frontend/CLAUDE.md, "Shared text components"): the
// website, and the kiosk tablet, read standing at arm's length.
export type TextSize = 'web' | 'kiosk';

// The colour of something that reports how things stand.
export type Tone = 'success' | 'warning' | 'danger' | 'neutral';

export const TONE_TEXT: Record<Tone, string> = {
	success: 'text-(--success-text)',
	warning: 'text-(--warning-text)',
	danger: 'text-(--danger-text)',
	neutral: 'text-(--text-muted)'
};

export const TONE_BOX: Record<Tone, string> = {
	success: 'bg-(--success-soft) text-(--success-text)',
	warning: 'bg-(--warning-soft) text-(--warning-text)',
	danger: 'bg-(--danger-soft) text-(--danger-text)',
	neutral: 'bg-(--surface-muted) text-(--text-muted)'
};
