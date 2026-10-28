<!--
    The family kiosk, one step at a time: mobile → PIN → (choose a new PIN,
    twice, the first time) → today's sessions. The first screen is the
    keypad itself, beside a welcome with the centre's sessions today
    (KioskWelcome). Forgot PIN emails a new one. Nothing is kept between
    people: the session token lives in this component only, and everything
    resets after 60 seconds without a tap, or 10 seconds after a sign-in or
    sign-out (a tap restarts that countdown).
-->
<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { scale } from 'svelte/transition';

	import { CircleCheck } from 'lucide-svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import ErrorText from '$lib/components/text/ErrorText.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import FamilyToday from './FamilyToday.svelte';
	import KioskSteps from './KioskSteps.svelte';
	import KioskWelcome from './KioskWelcome.svelte';
	import PhoneEntry from './PhoneEntry.svelte';
	import PinEntry from './PinEntry.svelte';

	import { createFamilyKioskApi } from '$lib/api/kiosk/adapters/familyKiosk';
	import type { KioskBookingResponse, KioskServiceTodayResponse } from '$lib/api/schema';
	import { DONE_LOGOUT_MS, SESSION_IDLE_MS, createTimer, formatClock, kioskToast, messageOf } from '../kiosk';

	let {
		locationCode
	}: {
		locationCode: string;
	} = $props();

	type Step = 'phone' | 'pin' | 'new-pin' | 'confirm-pin' | 'today' | 'forgot' | 'forgot-sent';

	// The centre's sessions today, for the welcome: refreshed whenever the
	// kiosk is back at the start, and every few minutes while it waits.
	const SESSIONS_REFRESH_MS = 5 * 60_000;

	const api = $derived(createFamilyKioskApi(locationCode));

	let step = $state<Step>('phone');
	let phone = $state('');
	let token = $state<string | null>(null);
	let firstName = $state('');
	let newPin = $state('');
	let bookings = $state<KioskBookingResponse[]>([]);
	let sessionsToday = $state<KioskServiceTodayResponse[]>([]);

	let error = $state<string | null>(null);
	let notice = $state<string | null>(null);
	let busy = $state(false);
	let busyBookingId = $state<string | null>(null);

	// After a sign-in or sign-out: what happened, and the countdown to logout.
	let done = $state<string | null>(null);
	let secondsLeft = $state(0);
	let countdown: ReturnType<typeof setInterval> | null = null;
	let sessionsTicker: ReturnType<typeof setInterval> | null = null;

	const idle = createTimer(SESSION_IDLE_MS, () => reset('idle'));

	// Why a person's turn ended, for the toast that says so.
	type EndReason = 'done' | 'finished' | 'idle' | 'expired' | 'cancelled';

	function announce(reason: EndReason, name: string, loggedIn: boolean) {
		if (reason === 'expired') {
			kioskToast.error('Your session ended. Please start again.');
		} else if (!loggedIn) {
			// Nobody had logged in yet (e.g. a half-typed number): nothing to say.
		} else if (reason === 'idle') {
			kioskToast.info(`${name ? `${name}, you were` : 'You were'} logged out after a minute without a tap.`);
		} else {
			kioskToast.success(`${name ? `Bye ${name}, you're` : "You're"} logged out.`);
		}
	}

	function reset(reason: EndReason = 'cancelled') {
		announce(reason, firstName, token !== null);

		stopCountdown();
		idle.stop();

		step = 'phone';
		phone = '';
		token = null;
		firstName = '';
		newPin = '';
		bookings = [];
		error = null;
		done = null;
		busy = false;
		busyBookingId = null;
		notice = null;

		void loadSessions();
	}

	async function loadSessions() {
		const response = await api.device();

		if (response.ok && response.data) sessionsToday = response.data.sessions_today;
	}

	function go(next: Step) {
		error = null;
		notice = null;
		step = next;
		idle.reset();
	}

	// Any tap keeps the person's session going, and restarts the logout
	// countdown after a sign-in or sign-out.
	function onTap() {
		// The start screen with nothing typed yet: nobody's session to keep.
		if (step === 'phone' && phone === '') return;

		idle.reset();

		if (done) startCountdown();
	}

	function startCountdown() {
		stopCountdown();
		secondsLeft = DONE_LOGOUT_MS / 1000;

		countdown = setInterval(() => {
			secondsLeft -= 1;

			if (secondsLeft <= 0) reset('finished');
		}, 1000);
	}

	function stopCountdown() {
		if (countdown) clearInterval(countdown);
		countdown = null;
	}

	// A 401 on a person's own action means their session ran out.
	function sessionEnded(status: number): boolean {
		if (status !== 401) return false;

		reset('expired');
		return true;
	}

	async function login(pin: string) {
		busy = true;
		error = null;

		try {
			const response = await api.login(phone, pin);

			if (!response.ok || !response.data) {
				error = messageOf(response);
				return;
			}

			token = response.data.session.token;
			firstName = response.data.first_name;

			kioskToast.success(`Hi ${firstName}, you're logged in.`);

			if (response.data.pin_change_required) {
				go('new-pin');
			} else {
				await loadToday();
			}
		} finally {
			busy = false;
		}
	}

	function chooseNewPin(pin: string) {
		newPin = pin;
		go('confirm-pin');
	}

	async function confirmNewPin(pin: string) {
		if (pin !== newPin || !token) {
			go('new-pin');
			error = "Those PINs didn't match. Choose your PIN again.";
			return;
		}

		busy = true;

		try {
			const response = await api.changePin(token, pin);

			if (sessionEnded(response.status)) return;

			if (!response.ok || !response.data) {
				go('new-pin');
				error = messageOf(response);
				return;
			}

			token = response.data.token;
			await loadToday();
		} finally {
			busy = false;
		}
	}

	async function loadToday() {
		if (!token) return;

		const response = await api.today(token);

		if (sessionEnded(response.status)) return;

		if (!response.ok || !response.data) {
			error = messageOf(response);
			return;
		}

		token = response.data.session.token;
		bookings = response.data.bookings;
		go('today');
	}

	async function sign(booking: KioskBookingResponse, action: 'in' | 'out') {
		if (!token) return;

		busyBookingId = booking.booking_id;
		error = null;

		try {
			const response = await api.sign(token, booking.booking_id, action);

			if (sessionEnded(response.status)) return;

			if (!response.ok || !response.data) {
				error = messageOf(response);
				return;
			}

			token = response.data.session.token;
			bookings = bookings.map((b) =>
				b.booking_id === booking.booking_id
					? { ...b, signed_in_at: response.data!.signed_in_at, signed_out_at: response.data!.signed_out_at }
					: b
			);

			const at = action === 'in' ? response.data.signed_in_at : response.data.signed_out_at;
			done = `${booking.child_first_name} signed ${action} at ${at ? formatClock(at) : 'now'}`;
			startCountdown();
		} finally {
			busyBookingId = null;
		}
	}

	async function forgotPin() {
		busy = true;

		try {
			const response = await api.forgotPin(phone);

			if (!response.ok) {
				error = messageOf(response);
				return;
			}

			notice = response.msg;
			step = 'forgot-sent';
			// Back to the start after a moment.
			setTimeout(() => {
				if (step === 'forgot-sent') reset();
			}, DONE_LOGOUT_MS);
		} finally {
			busy = false;
		}
	}

	onMount(() => {
		window.addEventListener('pointerdown', onTap, true);
		void loadSessions();

		sessionsTicker = setInterval(() => {
			if (step === 'phone') void loadSessions();
		}, SESSIONS_REFRESH_MS);
	});

	onDestroy(() => {
		window.removeEventListener('pointerdown', onTap, true);
		idle.stop();
		stopCountdown();
		if (sessionsTicker) clearInterval(sessionsTicker);
	});
</script>

{#snippet steps(current: 0 | 1 | 2)}
	<div class="pb-2">
		<KioskSteps {current} />
	</div>
{/snippet}

{#if step === 'phone'}
	<!-- The start: a welcome beside the keypad (landscape tablets). -->
	<div class="grid flex-1 grid-cols-1 items-start gap-10 py-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)]">
		<KioskWelcome sessions={sessionsToday} {notice} />

		<PhoneEntry title="Enter your mobile number" bind:phone onsubmit={() => go('pin')}>
			{#snippet footer()}
				<div class="flex flex-wrap justify-center gap-3">
					<Button variant="ghost" textSize="lg" onclick={() => go('forgot')}>Forgot PIN</Button>
					{#if phone}
						<Button variant="ghost" textSize="lg" onclick={() => reset()}>Clear</Button>
					{/if}
				</div>
			{/snippet}
		</PhoneEntry>
	</div>

{:else if step === 'pin'}
	{@render steps(1)}
	<PinEntry title="Enter your PIN" {error} {busy} oncomplete={login}>
		{#snippet footer()}
			<div class="flex flex-wrap justify-center gap-3">
				<Button variant="ghost" textSize="lg" onclick={() => go('forgot')}>Forgot PIN</Button>
				<Button variant="ghost" textSize="lg" onclick={() => reset()}>Cancel</Button>
			</div>
		{/snippet}
	</PinEntry>

{:else if step === 'new-pin'}
	{@render steps(1)}
	<PinEntry title={`Hi ${firstName}. Choose your own 4-digit PIN`} {error} {busy} oncomplete={chooseNewPin}>
		{#snippet footer()}
			<Button variant="ghost" textSize="lg" onclick={() => reset()}>Cancel</Button>
		{/snippet}
	</PinEntry>

{:else if step === 'confirm-pin'}
	{@render steps(1)}
	<PinEntry title="Enter your new PIN again" {error} {busy} oncomplete={confirmNewPin}>
		{#snippet footer()}
			<Button variant="ghost" textSize="lg" onclick={() => reset()}>Cancel</Button>
		{/snippet}
	</PinEntry>

{:else if step === 'today'}
	<div class="mx-auto flex w-full max-w-4xl flex-col gap-6">
		{@render steps(2)}

		{#if done}
			<!-- Signed in or out: big and clear, then logging out by itself. -->
			<div class="flex flex-col items-center gap-5 rounded-2xl border border-(--border) bg-(--success-soft) px-6 py-10 text-center" role="status">
				<span class="text-(--success-text)" in:scale={{ duration: 300, start: 0.5 }}>
					<CircleCheck size={88} strokeWidth={2.25} />
				</span>

				<p class="text-3xl font-extrabold text-(--success-text)">{done}</p>

				<div class="flex w-full max-w-md flex-col gap-2">
					<div class="h-2 w-full overflow-hidden rounded-full bg-(--surface)">
						<div
							class="h-full rounded-full bg-(--success-text) transition-[width] duration-1000 ease-linear"
							style:width={`${(secondsLeft / (DONE_LOGOUT_MS / 1000)) * 100}%`}
						></div>
					</div>
					<p class="text-lg text-(--success-text)">Logging out in {secondsLeft}…</p>
				</div>
			</div>
		{/if}

		<div class="flex items-center justify-between gap-4">
			<h1 class="text-3xl font-extrabold text-(--text)">Hi {firstName}</h1>
			<Button variant="ghost" textSize="lg" onclick={() => reset('done')}>Done</Button>
		</div>

		{#if error}
			<div class="text-center">
				<ErrorText size="kiosk" message={error} />
			</div>
		{/if}

		<FamilyToday {bookings} {busyBookingId} onsign={sign} />
	</div>

{:else if step === 'forgot'}
	<PhoneEntry title="Forgot your PIN?" bind:phone submitLabel="Email me a new PIN" {error} {busy} onsubmit={forgotPin}>
		{#snippet footer()}
			<p class="max-w-sm text-center text-lg text-(--text-muted)">
				We'll email a new PIN to the email address on your family's pickup list.
			</p>
			<Button variant="ghost" textSize="lg" onclick={() => reset()}>Cancel</Button>
		{/snippet}
	</PhoneEntry>

{:else if step === 'forgot-sent'}
	<div class="flex flex-1 flex-col items-center justify-center gap-6 py-12">
		<div class="w-full max-w-md">
			<Notice tone="success" size="kiosk">{notice}</Notice>
		</div>
		<Button variant="ghost" textSize="lg" onclick={() => reset()}>Back to start</Button>
	</div>
{/if}
