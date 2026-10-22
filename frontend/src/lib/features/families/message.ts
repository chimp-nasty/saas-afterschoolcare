// A message to a family is always "Dear {first name}," + what the admin
// wrote + the centre's sign-off. The admin writes only the middle; the
// form shows the rest read-only, and it's all sent as one message.

// The backend's limit on a message's whole text (SendFamilyMessageRequest).
const MESSAGE_MAX_LENGTH = 2000;

export type MessageFrame = {
	greeting: string;
	signOff: string;
};

export function messageFrame(familyFirstName: string, centreName: string): MessageFrame {
	return {
		greeting: `Dear ${familyFirstName},`,
		signOff: `Kind regards,\n${centreName} - Admin Team`
	};
}

export function composeMessage(frame: MessageFrame, body: string): string {
	return `${frame.greeting}\n\n${body.trim()}\n\n${frame.signOff}`;
}

// How much the admin can write, leaving room for the greeting and sign-off.
export function messageBodyMaxLength(frame: MessageFrame): number {
	return MESSAGE_MAX_LENGTH - composeMessage(frame, '').length;
}
