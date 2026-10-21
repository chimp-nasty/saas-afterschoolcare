<!--
    The family kiosk, one step at a time: Start → mobile → PIN → (choose a
    new PIN, twice, the first time) → today's sessions. Forgot PIN emails a
    new one. Nothing is kept between people: the session token lives in this
    component only, and everything resets after 60 seconds without a tap, or
    10 seconds after a sign-in or sign-out (a tap restarts that countdown).
-->
<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import FamilyToday from './FamilyToday.svelte';
	import PhoneEntry from './PhoneEntry.svelte';
	import PinEntry from './PinEntry.svelte';

	import { createFamilyKioskApi } from '$lib/api/kiosk/adapters/familyKiosk';
	import type { KioskBookingResponse } from '$lib/api/schema';
	import { DONE_LOGOUT_MS, SESSION_IDLE_MS, createTimer, formatClock, messageOf } from '../kiosk';

	let {
		locationCode
	}: {
		locationCode: string;
	} = $props();

	type Step = 'start' | 'phone' | 'pin' | 'new-pin' | 'confirm-pin' | 'today' | 'forgot' | 'forgot-sent';

	const api = $derived(createFamilyKioskApi(locationCode));

	let step = $state<Step>('start');
	let phone = $state('');
	let token = $state<string | null>(null);
	let firstName = $state('');
	let newPin = $state('');
	let bookings = $state<KioskBookingResponse[]>([]);

	let error = $state<string | null>(null);
	let notice = $state<string | null>(null);
	let busy = $state(false);
	let busyBookingId = $state<string | null>(null);

	// After a sign-in or sign-out: what happened, and the countdown to logout.
	let done = $state<string | null>(null);
	let secondsLeft = $state(0);
	let countdown: ReturnType<typeof setInterval> | null = null;

	const idle = createTimer(SESSION_IDLE_MS, () => reset());

	function reset(message: string | null = null) {
		stopCountdown();
		idle.stop();

		step = 'start';
		phone = '';
		token = null;
		firstName = '';
		newPin = '';
		bookings = [];
		error = null;
		done = null;
		busy = false;
		busyBookingId = null;
		notice = message;
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
		if (step === 'start') return;

		idle.reset();

		if (done) startCountdown();
	}

	function startCountdown() {
		stopCountdown();
		secondsLeft = DONE_LOGOUT_MS / 1000;

		countdown = setInterval(() => {
			secondsLeft -= 1;

			if (secondsLeft <= 0) reset();
		}, 1000);
	}

	function stopCountdown() {
		if (countdown) clearInterval(countdown);
		countdown = null;
	}

	// A 401 on a person's own action means their session ran out.
	function sessionEnded(status: number): boolean {
		if (status !== 401) return false;

		reset('Your session ended. Please start again.');
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

	onMount(() => window.addEventListener('pointerdown', onTap, true));

	onDestroy(() => {
		window.removeEventListener('pointerdown', onTap, true);
		idle.stop();
		stopCountdown();
	});
</script>

{#if step === 'start'}
	<div class="flex flex-1 flex-col items-center justify-center gap-8 py-12">
		<h1 class="text-center text-4xl font-extrabold text-(--text)">Welcome</h1>

		{#if notice}
			<p class="text-center text-lg text-(--text-muted)">{notice}</p>
		{/if}

		<div class="w-full max-w-sm">
			<Button fullWidth textSize="xl" class="min-h-20" onclick={() => go('phone')}>
				Sign in or out
			</Button>
		</div>
	</div>

{:else if step === 'phone'}
	<PhoneEntry title="Your mobile number" bind:phone onsubmit={() => go('pin')}>
		{#snippet footer()}
			<Button variant="ghost" onclick={() => reset()}>Cancel</Button>
		{/snippet}
	</PhoneEntry>

{:else if step === 'pin'}
	<PinEntry title="Enter your PIN" {error} {busy} oncomplete={login}>
		{#snippet footer()}
			<div class="flex flex-wrap justify-center gap-3">
				<Button variant="ghost" onclick={() => go('forgot')}>Forgot PIN</Button>
				<Button variant="ghost" onclick={() => reset()}>Cancel</Button>
			</div>
		{/snippet}
	</PinEntry>

{:else if step === 'new-pin'}
	<PinEntry title={`Hi ${firstName}. Choose your own 4-digit PIN`} {error} {busy} oncomplete={chooseNewPin}>
		{#snippet footer()}
			<Button variant="ghost" onclick={() => reset()}>Cancel</Button>
		{/snippet}
	</PinEntry>

{:else if step === 'confirm-pin'}
	<PinEntry title="Enter your new PIN again" {error} {busy} oncomplete={confirmNewPin}>
		{#snippet footer()}
			<Button variant="ghost" onclick={() => reset()}>Cancel</Button>
		{/snippet}
	</PinEntry>

{:else if step === 'today'}
	<div class="mx-auto flex w-full max-w-3xl flex-col gap-6">
		<div class="flex items-center justify-between gap-4">
			<h1 class="text-3xl font-extrabold text-(--text)">Hi {firstName}</h1>
			<Button variant="ghost" textSize="lg" onclick={() => reset()}>Done</Button>
		</div>

		{#if done}
			<Card border>
				<div class="flex flex-col items-center gap-3 text-center">
					<p class="text-2xl font-extrabold text-(--success-text)">✓ {done}</p>
					<p class="text-lg text-(--text-muted)">Logging out in {secondsLeft}…</p>
				</div>
			</Card>
		{/if}

		{#if error}
			<p class="text-center text-lg font-semibold text-(--danger-text)" role="alert">{error}</p>
		{/if}

		<FamilyToday {bookings} {busyBookingId} onsign={sign} />
	</div>

{:else if step === 'forgot'}
	<PhoneEntry title="Forgot your PIN?" bind:phone submitLabel="Email me a new PIN" {error} {busy} onsubmit={forgotPin}>
		{#snippet footer()}
			<p class="max-w-sm text-center text-base text-(--text-muted)">
				We'll email a new PIN to the email address on your family's pickup list.
			</p>
			<Button variant="ghost" onclick={() => reset()}>Cancel</Button>
		{/snippet}
	</PhoneEntry>

{:else if step === 'forgot-sent'}
	<div class="flex flex-1 flex-col items-center justify-center gap-6 py-12">
		<p class="max-w-md text-center text-2xl font-semibold text-(--text)">{notice}</p>
		<Button variant="ghost" textSize="lg" onclick={() => reset()}>Back to start</Button>
	</div>
{/if}
