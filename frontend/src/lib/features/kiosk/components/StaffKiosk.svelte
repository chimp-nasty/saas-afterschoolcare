<!--
    The staff kiosk (docs/portals.md), in tabs: the run sheet, shifts,
    medical and admin. Nobody is ever logged in: the run sheet and the shift
    list are always on show without personal details (refreshing every 20
    seconds), and everything else is a task. A task starts with "Who are
    you?" (only people on shift) or, for clocking in or out, choosing your
    name from everyone, and that person's staff PIN, which is kept here in
    memory for that task only and sent with each of its requests. The task
    ends, and the PIN is forgotten, when its action is done, when it's
    cancelled, or after 60 seconds without a tap. A one-off release asks for
    the PIN again.
-->
<script lang="ts">
	import { onDestroy, onMount, tick } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import PrintableRunSheet, { type PrintSession } from '$lib/features/attendance/components/PrintableRunSheet.svelte';
	import TabbedPanels from '$lib/components/controls/TabbedPanels.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Select from '$lib/components/forms/fields/Select.svelte';
	import Modal from '$lib/components/overlays/Modal.svelte';
	import { confirmAction } from '$lib/components/overlays/confirm.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import ErrorText from '$lib/components/text/ErrorText.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import KioskScreen from './KioskScreen.svelte';
	import PinEntry from './PinEntry.svelte';
	import StaffActionPlans from './StaffActionPlans.svelte';
	import StaffBulkPanel from './StaffBulkPanel.svelte';
	import StaffFamilyBookings from './StaffFamilyBookings.svelte';
	import StaffChildPanel from './StaffChildPanel.svelte';
	import StaffIdentify from './StaffIdentify.svelte';
	import StaffMedicalPanel from './StaffMedicalPanel.svelte';
	import StaffNotesPanel from './StaffNotesPanel.svelte';
	import StaffRoll from './StaffRoll.svelte';
	import StaffShifts from './StaffShifts.svelte';

	import { createStaffKioskApi, type StaffCredentials } from '$lib/api/kiosk/adapters/staffKiosk';
	import type { ApiResponse } from '$lib/api/wrapper';
	import type {
		ActionPlanResponse,
		ChildMedicalResponse,
		ChildNoteResponse,
		ChildSearchResultResponse,
		FamilyBookingResponse,
		RollPickupPersonResponse,
		RollResponse,
		RunSheetEntryResponse,
		StaffKioskMemberResponse,
		RunSheetSessionResponse
	} from '$lib/api/schema';
	import { kioskChildTabs, kioskTabs } from '$lib/navigation/tabs';
	import { formatDate, formatMoney, formatTimestamp } from '$lib/utils/helpers';
	import {
		ROLL_REFRESH_MS,
		SESSION_IDLE_MS,
		createTimer,
		messageOf,
		readClockedOut,
		saveClockedOut,
		type ClockedOut
	} from '../kiosk';
	import { openDocument } from '../medical';

	type Release = { released_to_name: string; release_note: string };

	type Task =
		| { kind: 'child'; bookingId: string; name: string }
		| {
				kind: 'bulk';
				action: 'sign_in' | 'to_school';
				name: string;
				candidates: RunSheetEntryResponse[];
		  }
		| { kind: 'shift' }
		// The action plan list: shown on the Medical tab until the task ends.
		| { kind: 'plans' }
		// The printable run sheet for one session.
		| { kind: 'print'; session: RunSheetSessionResponse }
		// An admin refunding one of a family's bookings.
		| { kind: 'refund' };

	// Where the task is up to. A child: choosing who you are and entering
	// your PIN, the child's panel, and the re-entered PIN for a one-off
	// release. A shift: choosing your name, when you left a shift you didn't
	// clock out of (if any), then your PIN, which clocks you in or out.
	type Step =
		| 'identify'
		| 'child'
		| 'bulk'
		| 'repin'
		| 'shift-choose'
		| 'shift-left'
		| 'shift-pin'
		| 'plans'
		| 'refund-search'
		| 'refund-bookings'
		| 'refund-pin';

	// How long the outcome of a task stays on screen.
	const NOTICE_MS = 5_000;

	const tabs = [
		{ id: kioskTabs.RUN_SHEET, label: 'Run sheet' },
		{ id: kioskTabs.SHIFTS, label: 'Shifts' },
		{ id: kioskTabs.MEDICAL, label: 'Medical' },
		{ id: kioskTabs.ADMIN, label: 'Admin' }
	];

	let {
		locationCode,
		centreName
	}: {
		locationCode: string;
		centreName: string;
	} = $props();

	const api = $derived(createStaffKioskApi(locationCode));

	let activeTab = $state<string>(kioskTabs.RUN_SHEET);

	// On show without a PIN.
	let date = $state('');
	let today = $state('');
	let board = $state<RunSheetEntryResponse[]>([]);
	let sessions = $state<RunSheetSessionResponse[]>([]);
	let boardError = $state<string | null>(null);
	let members = $state<StaffKioskMemberResponse[]>([]);

	// The current task.
	let task = $state<Task | null>(null);
	let step = $state<Step>('identify');
	let staff = $state<(StaffCredentials & { firstName: string }) | null>(null);
	let roll = $state<RollResponse | null>(null);
	let release = $state<(Release & { at: string | null; alsoBookingIds: string[] }) | null>(null);
	let shiftMemberId = $state('');
	let leftAt = $state('');
	let clockedOut = $state<ClockedOut[]>([]);
	let busy = $state(false);
	let taskError = $state<string | null>(null);
	// The child's Medical tab, loaded when it's first opened in the task.
	let childTab = $state<string>(kioskChildTabs.ATTENDANCE);
	let medical = $state<ChildMedicalResponse | null>(null);
	let medicalError = $state<string | null>(null);
	// The child's Notes tab (staff's notes), loaded the same way.
	let notes = $state<ChildNoteResponse[] | null>(null);
	let notesError = $state<string | null>(null);
	let plans = $state<ActionPlanResponse[] | null>(null);
	// A family's bookings: the child's Bookings tab, or an admin's refund.
	let familyBookings = $state<FamilyBookingResponse[] | null>(null);
	let familyBookingsError = $state<string | null>(null);
	// An admin's refund: finding the family, then the booking.
	let searchText = $state('');
	let searchResults = $state<ChildSearchResultResponse[] | null>(null);
	let refundFamily = $state<ChildSearchResultResponse | null>(null);
	let refundBooking = $state<FamilyBookingResponse | null>(null);
	// What's being printed: kept after the task ends, until printing's done.
	let printJob = $state<{ sessions: PrintSession[]; roll: RollResponse } | null>(null);
	let pinError = $state<string | null>(null);

	const bookingId = $derived(task?.kind === 'child' ? task.bookingId : null);
	const entry = $derived(roll?.entries.find((e) => e.booking_id === bookingId) ?? null);
	const pickups = $derived<RollPickupPersonResponse[]>(
		entry ? (roll?.families.find((f) => f.family_user_id === entry.family_user_id)?.pickups ?? []) : []
	);
	// This family's other children who are here, to go with them.
	const siblings = $derived(
		entry
			? (roll?.entries ?? []).filter(
					(e) =>
						e.family_user_id === entry.family_user_id &&
						e.booking_id !== entry.booking_id &&
						!!e.signed_in_at &&
						!e.signed_out_at
				)
			: []
	);
	const hasMedical = $derived(board.find((b) => b.booking_id === bookingId)?.has_medical ?? false);
	const hasNotes = $derived(board.find((b) => b.booking_id === bookingId)?.has_notes ?? false);

	// Before school children (here) can be sent to school from their panel.
	const canSendToSchool = $derived(
		!!entry &&
			sessions.some(
				(session) =>
					session.service_code === 'before_school_care' &&
					session.service_name === entry.service_name &&
					session.start_time === entry.start_time
			)
	);
	const shiftMember = $derived(members.find((m) => m.user_id === shiftMemberId) ?? null);
	const clockable = $derived(members.filter((m) => m.has_pin));

	let notice = $state<{ text: string; tone: 'success' | 'danger' } | null>(null);
	let noticeTimer: ReturnType<typeof setTimeout> | null = null;

	let taskModal: Modal;
	const idle = createTimer(SESSION_IDLE_MS, () => endTask());
	let refresher: ReturnType<typeof setInterval> | null = null;

	const title = $derived.by(() => {
		if (!task) return 'Staff';
		if (task.kind === 'plans') return 'Action plans';
		if (task.kind === 'print') return 'Print run sheet';
		if (task.kind === 'refund') {
			return refundFamily ? `Refund · ${refundFamily.family_first_name} ${refundFamily.family_last_name}` : 'Refund';
		}
		if (task.kind === 'shift') {
			if (step === 'shift-choose' || !shiftMember) return 'Clock in or out';

			return shiftMember.on_shift ? 'Clock out' : 'Clock in';
		}
		if (step === 'identify') return 'Staff';
		if (step === 'repin') return 'Confirm the release';
		if (task.kind === 'bulk') {
			return `${task.action === 'sign_in' ? 'Sign in arrivals' : 'Send to school'} · ${task.name}`;
		}

		return task.name;
	});

	async function loadBoard() {
		// Today is always asked for without a date, so the screen moves on to
		// the next day by itself after midnight.
		const requested = date && date !== today ? date : undefined;
		const response = await api.board(requested);

		if (!response.ok || !response.data) {
			boardError = messageOf(response);
			return;
		}

		boardError = null;
		board = response.data.entries;
		sessions = response.data.sessions;

		if (!requested) {
			date = response.data.date;

			if (today !== response.data.date) {
				today = response.data.date;
				clockedOut = readClockedOut(locationCode, today);
			}
		}
	}

	async function loadMembers() {
		const response = await api.staff();
		if (response.ok && response.data) members = response.data;
	}

	function refresh() {
		void loadBoard();
		void loadMembers();
	}

	// The full roll for this task's day, as the task's staff member.
	async function loadRoll(): Promise<string | null> {
		if (!staff) return null;

		const response = await api.roll(staff, date || undefined);

		if (!response.ok || !response.data) return messageOf(response);

		roll = response.data;

		return null;
	}

	function showNotice(text: string, tone: 'success' | 'danger' = 'success') {
		notice = { text, tone };
		if (noticeTimer) clearTimeout(noticeTimer);
		noticeTimer = setTimeout(() => (notice = null), NOTICE_MS);
	}

	function startTask(next: Task) {
		task = next;
		staff = null;
		roll = null;
		release = null;
		medical = null;
		medicalError = null;
		notes = null;
		notesError = null;
		familyBookings = null;
		familyBookingsError = null;
		searchText = '';
		searchResults = null;
		refundFamily = null;
		refundBooking = null;
		childTab = kioskChildTabs.ATTENDANCE;
		shiftMemberId = '';
		leftAt = '';
		taskError = null;
		pinError = null;
		step = next.kind === 'shift' ? 'shift-choose' : 'identify';
		void loadMembers();

		idle.reset();
		taskModal.open();
	}

	// Ends the task and forgets the PIN. Safe to call twice (closing the
	// modal calls it again).
	function endTask(message?: { text: string; tone?: 'success' | 'danger' }) {
		if (!task) return;

		task = null;
		staff = null;
		roll = null;
		release = null;
		medical = null;
		notes = null;
		plans = null;
		familyBookings = null;
		searchResults = null;
		refundFamily = null;
		refundBooking = null;
		idle.stop();
		taskModal.close();

		if (message) showNotice(message.text, message.tone);

		refresh();
	}

	async function verify(member: StaffKioskMemberResponse, pin: string): Promise<string | null> {
		const credentials = { userId: member.user_id, pin };
		const response = await api.verify(credentials);

		if (!response.ok || !response.data) return messageOf(response);

		staff = { ...credentials, firstName: response.data.first_name };
		idle.reset();

		if (task?.kind === 'bulk') {
			step = 'bulk';
			return null;
		}

		if (task?.kind === 'refund') {
			step = 'refund-search';
			return null;
		}

		if (task?.kind === 'print') {
			const error = await loadRoll();
			if (error || !roll) return error;

			await print(task.session, roll);
			return null;
		}

		if (task?.kind === 'plans') {
			const plansResponse = await api.actionPlans(credentials);

			if (!plansResponse.ok || !plansResponse.data) return messageOf(plansResponse);

			plans = plansResponse.data;
			step = 'plans';
			taskModal.close();
			return null;
		}

		const error = await loadRoll();
		if (error) return error;

		if (!entry) {
			endTask({ text: 'That booking is no longer on the run sheet.', tone: 'danger' });
			return null;
		}

		step = 'child';

		return null;
	}

	// One request in the task. A 401 or 403 means this person can't act any
	// more (PIN locked or changed, or clocked out elsewhere), so the task
	// ends.
	async function run<T>(request: (credentials: StaffCredentials) => Promise<ApiResponse<T>>): Promise<T | null> {
		if (!staff) return null;

		busy = true;
		taskError = null;

		try {
			const response = await request(staff);

			if (response.status === 401 || response.status === 403) {
				endTask({ text: messageOf(response), tone: 'danger' });
				return null;
			}

			if (!response.ok || !response.data) {
				taskError = messageOf(response);
				return null;
			}

			idle.reset();

			return response.data;
		} finally {
			busy = false;
		}
	}

	async function signIn(at: string | null) {
		if (!entry) return;

		const name = entry.child_first_name;

		if (await run((as) => api.sign(as, { booking_id: entry.booking_id, action: 'in', at }))) {
			endTask({ text: `${name} signed in` });
		}
	}

	// "Emma", "Emma and Noah", "Emma, Noah and Ava".
	function names(bookingIds: string[]): string {
		const first = bookingIds.map((id) => roll?.entries.find((e) => e.booking_id === id)?.child_first_name ?? 'A child');

		return first.length === 1 ? first[0] : `${first.slice(0, -1).join(', ')} and ${first[first.length - 1]}`;
	}

	// Signs out to someone on the pickup list, with any brothers and sisters
	// going too (one request, all or nothing, even for one child). Someone not approved yet is
	// approved without ID first (the panel has already asked).
	async function collect(person: RollPickupPersonResponse, at: string | null, alsoBookingIds: string[]) {
		if (!entry) return;

		const bookingIds = [entry.booking_id, ...alsoBookingIds];
		const who = names(bookingIds);

		if (!person.staff_approved_at && !(await run((as) => api.checkId(as, person.pickup_person_id, false)))) {
			return;
		}

		const out = { collected_by_pickup_person_id: person.pickup_person_id };
		const signedOut = await run((as) => api.bulk(as, 'sign_out', bookingIds, at, out));

		if (signedOut) {
			endTask({ text: `${who} signed out to ${person.first_name}` });
		} else if (task) {
			// The approval may have gone through: show it.
			await loadRoll();
		}
	}

	// A one-off release asks for the PIN again first.
	function startRelease(details: Release, at: string | null, alsoBookingIds: string[]) {
		release = { ...details, at, alsoBookingIds };
		pinError = null;
		step = 'repin';
	}

	// The release, sent with the PIN just re-entered. A wrong one stays here
	// for another try; any other problem goes back to the panel.
	async function confirmRelease(pin: string) {
		if (!staff || !entry || !release) return;

		const { at, alsoBookingIds, ...details } = release;
		const bookingIds = [entry.booking_id, ...alsoBookingIds];
		const who = names(bookingIds);
		const credentials = { userId: staff.userId, pin };

		busy = true;

		try {
			const response = await api.bulk(credentials, 'sign_out', bookingIds, at, details);

			if (response.status === 401) {
				pinError = messageOf(response);
				return;
			}

			if (!response.ok) {
				taskError = messageOf(response);
				step = 'child';
				return;
			}

			endTask({ text: `${who} released to ${details.released_to_name}` });
		} finally {
			busy = false;
		}
	}

	async function sendToSchool(at: string | null) {
		if (!entry) return;

		const name = entry.child_first_name;

		if (await run((as) => api.sign(as, { booking_id: entry.booking_id, action: 'out', at, sent_to_school: true }))) {
			endTask({ text: `${name} sent to school` });
		}
	}

	// Several children at once, all or nothing.
	async function submitBulk(bookingIds: string[], at: string | null) {
		if (task?.kind !== 'bulk') return;

		const action = task.action;
		const done = await run((as) => api.bulk(as, action, bookingIds, at));

		if (done) {
			const children = `${done.length} ${done.length === 1 ? 'child' : 'children'}`;
			endTask({ text: action === 'sign_in' ? `${children} signed in` : `${children} sent to school` });
		}
	}

	$effect(() => {
		if (step === 'child' && childTab === kioskChildTabs.MEDICAL && entry && !medical && !medicalError) {
			void loadMedical(entry.child_id);
		}
	});

	$effect(() => {
		if (step === 'child' && childTab === kioskChildTabs.NOTES && entry && !notes && !notesError) {
			void loadNotes(entry.child_id);
		}
	});

	async function loadNotes(childId: string) {
		if (!staff) return;

		const response = await api.notes(staff, childId);

		if (response.status === 401 || response.status === 403) {
			endTask({ text: messageOf(response), tone: 'danger' });
			return;
		}

		if (response.ok && response.data) notes = response.data;
		else notesError = messageOf(response);
	}

	async function loadMedical(childId: string) {
		if (!staff) return;

		const response = await api.medical(staff, childId);

		if (response.status === 401 || response.status === 403) {
			endTask({ text: messageOf(response), tone: 'danger' });
			return;
		}

		if (response.ok && response.data) medical = response.data;
		else medicalError = messageOf(response);
	}

	// Ticks (or unticks) a plan as printed, as the staff member whose PIN
	// opened the list, then shows the list again.
	async function setPrinted(documentId: string, printed: boolean) {
		if (!(await run((as) => api.setPrinted(as, documentId, printed)))) {
			if (taskError) showNotice(taskError, 'danger');
		}

		if (!staff) return;

		const response = await api.actionPlans(staff);
		if (response.ok && response.data) plans = response.data;
	}

	$effect(() => {
		if (step === 'child' && childTab === kioskChildTabs.BOOKINGS && entry && !familyBookings && !familyBookingsError) {
			void loadFamilyBookings(entry.family_user_id);
		}
	});

	async function loadFamilyBookings(familyUserId: string) {
		if (!staff) return;

		const response = await api.familyBookings(staff, familyUserId);

		if (response.status === 401 || response.status === 403) {
			endTask({ text: messageOf(response), tone: 'danger' });
			return;
		}

		if (response.ok && response.data) familyBookings = response.data;
		else familyBookingsError = messageOf(response);
	}

	// An admin's refund: find the family by a child's name.
	async function searchFamilies() {
		if (searchText.trim().length < 2) return;

		const results = await run((as) => api.searchChildren(as, searchText.trim()));
		if (results) searchResults = results;
	}

	async function chooseFamily(child: ChildSearchResultResponse) {
		refundFamily = child;
		familyBookings = null;
		familyBookingsError = null;
		step = 'refund-bookings';
		await loadFamilyBookings(child.family_user_id);
	}

	// Confirm, then the admin enters their PIN again.
	async function startRefund(booking: FamilyBookingResponse) {
		const confirmed = await confirmAction({
			title: `Refund ${booking.child_name}'s ${booking.service_name.toLowerCase()} on ${formatDate(booking.service_date)}?`,
			message: `${formatMoney(booking.price_snapshot_cents, booking.currency)} goes back to the card it was paid with, and the booking is cancelled. You'll enter your PIN again to confirm.`,
			confirmLabel: 'Refund',
			tone: 'danger'
		});

		if (!confirmed) return;

		refundBooking = booking;
		pinError = null;
		step = 'refund-pin';
	}

	// The refund, sent with the PIN just re-entered.
	async function confirmRefund(pin: string) {
		if (!staff || !refundBooking) return;

		const booking = refundBooking;

		busy = true;

		try {
			const response = await api.refund({ userId: staff.userId, pin }, booking.id);

			if (response.status === 401) {
				pinError = messageOf(response);
				return;
			}

			if (!response.ok) {
				familyBookingsError = null;
				taskError = messageOf(response);
				step = 'refund-bookings';
				return;
			}

			endTask({ text: `Refund requested for ${booking.child_name}, ${formatDate(booking.service_date)}` });
		} finally {
			busy = false;
		}
	}

	// Opens a document in a new tab, as the task's staff member.
	async function viewDocument(documentId: string) {
		const error = await openDocument(async () => (await run((as) => api.download(as, documentId)))?.url ?? null);

		if (error) showNotice(error, 'danger');
	}

	// Photo ID checked: also approves them. The task carries on.
	async function checkId(person: RollPickupPersonResponse) {
		if (await run((as) => api.checkId(as, person.pickup_person_id, true))) {
			const error = await loadRoll();
			if (error) taskError = error;
		}
	}

	async function undo(undoStep: 'sign_in' | 'sign_out') {
		if (!entry) return;

		if (await run((as) => api.undo(as, entry.booking_id, undoStep))) {
			endTask({ text: undoStep === 'sign_out' ? 'Sign-out undone' : 'Sign-in undone' });
		}
	}

	// The local date ("YYYY-MM-DD") a timestamp falls on, at the tablet (it's
	// at the centre).
	function localDay(value: string): string {
		const day = new Date(value);
		const month = String(day.getMonth() + 1).padStart(2, '0');

		return `${day.getFullYear()}-${month}-${String(day.getDate()).padStart(2, '0')}`;
	}

	function chooseShiftMember() {
		if (!shiftMember) return;

		taskError = null;
		step = shiftMember.unclosed_shift_started_at ? 'shift-left' : 'shift-pin';
	}

	// Clock in or out with the PIN just entered, closing a forgotten shift
	// with the time they gave.
	async function clock(pin: string) {
		if (!shiftMember) return;

		const member = shiftMember;
		const action = member.on_shift ? 'end' : 'start';
		const previousEndedAt =
			member.unclosed_shift_started_at && leftAt
				? new Date(`${localDay(member.unclosed_shift_started_at)}T${leftAt}`).toISOString()
				: undefined;

		busy = true;

		try {
			const response = await api.shift({ userId: member.user_id, pin }, action, previousEndedAt);

			if (response.status === 401) {
				pinError = messageOf(response);
				return;
			}

			if (!response.ok) {
				// The time they left didn't fit: ask again.
				taskError = messageOf(response);
				step = member.unclosed_shift_started_at ? 'shift-left' : 'shift-pin';
				return;
			}

			if (action === 'end' && response.data?.ended_at && today) {
				clockedOut = [
					...clockedOut,
					{
						userId: member.user_id,
						name: `${member.first_name} ${member.last_name}`,
						startedAt: response.data.started_at ?? null,
						endedAt: response.data.ended_at
					}
				];
				saveClockedOut(locationCode, today, clockedOut);
			}

			endTask({ text: `${member.first_name} clocked ${action === 'start' ? 'in' : 'out'}` });
		} finally {
			busy = false;
		}
	}

	// Prints one session's run sheet, then ends the task (the PIN isn't
	// needed once it's on paper).
	async function print(session: RunSheetSessionResponse, fullRoll: RollResponse) {
		printJob = {
			roll: fullRoll,
			sessions: [
				{
					name: session.service_name,
					startTime: session.start_time,
					endTime: session.end_time,
					entries: fullRoll.entries.filter(
						(e) => e.service_name === session.service_name && e.start_time === session.start_time
					)
				}
			]
		};

		endTask();
		await tick();
		window.print();
	}

	function afterPrint() {
		printJob = null;
	}

	function onTap() {
		if (task) idle.reset();
	}

	onMount(() => {
		refresh();
		refresher = setInterval(refresh, ROLL_REFRESH_MS);
		window.addEventListener('pointerdown', onTap, true);
		window.addEventListener('afterprint', afterPrint);
	});

	onDestroy(() => {
		if (refresher) clearInterval(refresher);
		if (noticeTimer) clearTimeout(noticeTimer);
		window.removeEventListener('pointerdown', onTap, true);
		window.removeEventListener('afterprint', afterPrint);
		idle.stop();
	});
</script>

<KioskScreen {centreName} label="Staff kiosk">
	<div class="flex flex-col gap-6">
		{#if notice}
			<Notice tone={notice.tone} size="kiosk">{notice.text}</Notice>
		{/if}

		<TabbedPanels {tabs} bind:activeTab>
			{#snippet panel(id)}
				{#if id === kioskTabs.RUN_SHEET}
					<div class="flex flex-col gap-6">
						<div class="flex flex-wrap items-end justify-between gap-4">
							<label class="flex flex-col gap-1">
								<span class="label-text">Day</span>
								<input type="date" max={today || undefined} bind:value={date} onchange={() => void loadBoard()} />
							</label>

							<div class="flex flex-wrap gap-3">
								{#if date && today && date !== today}
									<Button variant="ghost" onclick={() => { date = today; void loadBoard(); }}>Back to today</Button>
								{/if}
							</div>
						</div>

						<ErrorText size="kiosk" message={boardError} />

						<!-- A new day picks its default session tab again. -->
						{#key date}
							<StaffRoll
								{sessions}
								entries={board}
								isToday={!!date && date === today}
								isPast={!!date && !!today && date < today}
								onselect={(selected) =>
									startTask({ kind: 'child', bookingId: selected.booking_id, name: `${selected.child_first_name} ${selected.child_last_name}` })}
								onbulk={(action, session, candidates) =>
									startTask({ kind: 'bulk', action, name: session.service_name, candidates })}
								onprint={(session) => startTask({ kind: 'print', session })}
							/>
						{/key}
					</div>
				{:else if id === kioskTabs.SHIFTS}
					<StaffShifts {members} {clockedOut} onclock={() => startTask({ kind: 'shift' })} />
				{:else if id === kioskTabs.MEDICAL}
					<StaffActionPlans
						{plans}
						shownTo={task?.kind === 'plans' ? (staff?.firstName ?? null) : null}
						onshow={() => startTask({ kind: 'plans' })}
						onhide={() => endTask()}
						onview={viewDocument}
						onprinted={setPrinted}
					/>
				{:else if id === kioskTabs.ADMIN}
					<section class="flex flex-col gap-3">
						<SectionHeading
							size="kiosk"
							title="Refunds"
							description="Admins only. One booking (one child, one day) at a time, in full, up to and including its day."
						>
							{#snippet actions()}
								<Button onclick={() => startTask({ kind: 'refund' })}>Start a refund</Button>
							{/snippet}
						</SectionHeading>
					</section>
				{/if}
			{/snippet}
		</TabbedPanels>
	</div>
</KioskScreen>

<Modal
	bind:this={taskModal}
	{title}
	dismissible={!busy}
	onclose={() => {
		if (!(task?.kind === 'plans' && step === 'plans')) endTask();
	}}
>
	{#if task}
		{#if step === 'identify' && task.kind !== 'shift'}
			<StaffIdentify
				{members}
				adminsOnly={task.kind === 'refund'}
				task={task.kind === 'bulk'
					? `${task.candidates.length} children in ${task.name}`
					: task.kind === 'plans'
						? 'the action plans'
						: task.kind === 'print'
							? `the ${task.session.service_name} run sheet`
							: task.kind === 'refund'
								? 'a refund'
								: task.name}
				onverify={verify}
				oncancel={() => endTask()}
			/>
		{:else if step === 'bulk' && task.kind === 'bulk'}
			<StaffBulkPanel
				action={task.action}
				{date}
				candidates={task.candidates}
				{busy}
				error={taskError}
				onsubmit={submitBulk}
				oncancel={() => endTask()}
			/>
		{:else if step === 'child' && entry}
			<div class="flex flex-col gap-4">
				{#if hasMedical && childTab === kioskChildTabs.ATTENDANCE}
					<Notice tone="danger" size="kiosk">
						⚠ {entry.child_first_name} has medical details
						{#snippet actions()}
							<Button variant="ghost" onclick={() => (childTab = kioskChildTabs.MEDICAL)}>See medical</Button>
						{/snippet}
					</Notice>
				{/if}

				{#if hasNotes && childTab === kioskChildTabs.ATTENDANCE}
					<Notice tone="neutral" size="kiosk">
						Staff have notes about {entry.child_first_name}
						{#snippet actions()}
							<Button variant="ghost" onclick={() => (childTab = kioskChildTabs.NOTES)}>See notes</Button>
						{/snippet}
					</Notice>
				{/if}

				<TabbedPanels
					tabs={[
						{ id: kioskChildTabs.ATTENDANCE, label: 'Attendance' },
						{ id: kioskChildTabs.MEDICAL, label: 'Medical' },
						{ id: kioskChildTabs.NOTES, label: 'Notes' },
						{ id: kioskChildTabs.BOOKINGS, label: 'Bookings' }
					]}
					bind:activeTab={childTab}
				>
					{#snippet panel(tabId)}
						{#if tabId === kioskChildTabs.MEDICAL}
							<StaffMedicalPanel {medical} error={medicalError} onview={viewDocument} />
						{:else if tabId === kioskChildTabs.NOTES}
							<StaffNotesPanel {notes} error={notesError} />
						{:else if tabId === kioskChildTabs.BOOKINGS}
							<StaffFamilyBookings bookings={familyBookings} error={familyBookingsError} />
						{:else}
							<StaffChildPanel
								{entry}
								{date}
								{pickups}
								{siblings}
								{busy}
								error={taskError}
								onsignin={signIn}
								oncollect={collect}
								onrelease={startRelease}
								oncheckid={checkId}
								onundo={undo}
								{canSendToSchool}
								onsendtoschool={sendToSchool}
							/>
						{/if}
					{/snippet}
				</TabbedPanels>
			</div>
		{:else if step === 'repin' && staff && release}
			<PinEntry
				title={`${staff.firstName}, re-enter your PIN to release ${names([entry?.booking_id ?? '', ...release.alsoBookingIds])} to ${release.released_to_name}`}
				error={pinError}
				{busy}
				oncomplete={confirmRelease}
			>
				{#snippet footer()}
					<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => (step = 'child')}>Back</Button>
				{/snippet}
			</PinEntry>
		{:else if step === 'refund-search'}
			<form
				class="flex flex-col gap-4"
				onsubmit={(event) => {
					event.preventDefault();
					void searchFamilies();
				}}
			>
				<Field label="Child's first or last name">
					{#snippet children(id)}
						<input {id} type="search" autocomplete="off" minlength="2" bind:value={searchText} />
					{/snippet}
				</Field>

				<div class="grid grid-cols-2 gap-3">
					<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => endTask()}>Cancel</Button>
					<Button type="submit" fullWidth isLoading={busy} isDisabled={busy || searchText.trim().length < 2}>Find</Button>
				</div>

				{#if searchResults}
					<ul class="flex max-h-[40vh] flex-col overflow-y-auto rounded-lg border border-(--border)">
						{#each searchResults as child (child.child_id)}
							<li class="border-b border-(--border) last:border-b-0">
								<button
									type="button"
									class="flex min-h-12 w-full flex-col px-4 py-2 text-left active:bg-(--primary-soft)"
									onclick={() => chooseFamily(child)}
								>
									<span class="text-base font-semibold text-(--text)">{child.first_name} {child.last_name}</span>
									<span class="text-sm text-(--text-muted)">Family: {child.family_first_name} {child.family_last_name}</span>
								</button>
							</li>
						{:else}
							<li class="px-4"><EmptyState size="kiosk" message="No children found." /></li>
						{/each}
					</ul>
				{/if}
			</form>
		{:else if step === 'refund-bookings'}
			<div class="flex flex-col gap-4">
				<ErrorText size="kiosk" message={taskError} />

				<StaffFamilyBookings bookings={familyBookings} error={familyBookingsError} {busy} onrefund={startRefund} />

				<div class="grid grid-cols-2 gap-3">
					<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => (step = 'refund-search')}>Back</Button>
					<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => endTask()}>Done</Button>
				</div>
			</div>
		{:else if step === 'refund-pin' && staff && refundBooking}
			<PinEntry
				title={`${staff.firstName}, re-enter your PIN to refund ${refundBooking.child_name}, ${formatDate(refundBooking.service_date)}`}
				error={pinError}
				{busy}
				oncomplete={confirmRefund}
			>
				{#snippet footer()}
					<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => (step = 'refund-bookings')}>Back</Button>
				{/snippet}
			</PinEntry>
		{:else if step === 'shift-choose'}
			<div class="flex flex-col gap-5">
				<Field label="Who are you?">
					{#snippet children(id)}
						<Select
							{id}
							bind:value={shiftMemberId}
							size="kiosk"
							placeholder="Choose your name"
							options={clockable.map((member) => ({
								value: member.user_id,
								label: `${member.first_name} ${member.last_name}${member.on_shift ? ' (on shift)' : ''}`
							}))}
						/>
					{/snippet}
				</Field>

				<p class="text-sm text-(--text-muted)">Not listed? Set your staff PIN on the website (My account) first.</p>

				<div class="grid grid-cols-2 gap-3">
					<Button variant="ghost" fullWidth onclick={() => endTask()}>Cancel</Button>
					<Button fullWidth isDisabled={!shiftMember} onclick={chooseShiftMember}>
						{shiftMember?.on_shift ? 'Clock out' : 'Clock in'}
					</Button>
				</div>
			</div>
		{:else if step === 'shift-left' && shiftMember?.unclosed_shift_started_at}
			<div class="flex flex-col gap-5">
				<p class="text-lg text-(--text)">
					{shiftMember.first_name}, you didn't clock out of your shift on
					{formatTimestamp(shiftMember.unclosed_shift_started_at)}. What time did you leave?
				</p>

				<Field label="Time you left">
					{#snippet children(id)}
						<input {id} type="time" bind:value={leftAt} required />
					{/snippet}
				</Field>

				<ErrorText size="kiosk" message={taskError} />

				<div class="grid grid-cols-2 gap-3">
					<Button variant="ghost" fullWidth onclick={() => (step = 'shift-choose')}>Back</Button>
					<Button fullWidth isDisabled={!leftAt} onclick={() => { taskError = null; step = 'shift-pin'; }}>Continue</Button>
				</div>
			</div>
		{:else if step === 'shift-pin' && shiftMember}
			<PinEntry
				title={`${shiftMember.first_name}, enter your PIN to clock ${shiftMember.on_shift ? 'out' : 'in'}`}
				error={pinError ?? taskError}
				{busy}
				oncomplete={clock}
			>
				{#snippet footer()}
					<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => (step = 'shift-choose')}>Not me</Button>
				{/snippet}
			</PinEntry>
		{/if}
	{/if}
</Modal>

{#if printJob}
	<PrintableRunSheet
		{centreName}
		date={printJob.roll.date}
		sessions={printJob.sessions}
		families={printJob.roll.families}
	/>
{/if}
