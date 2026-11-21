// Everything about how the decision card moves, waits and hints. Change the feel of the deck here.
// Times in ms unless the name ends in _S (seconds); distances in px.

// ---------- Deciding (drag and hold) ----------
// How far the card has to be dragged before holding starts to count.
export const SWIPE_X = 110;
// Hold time to confirm a decision; longer above the "extra confirm" amount set in Rules.
export const HOLD_MS = 600;
export const HOLD_BIG_MS = 1200;
// Movement under which a press still counts as a tap (flip).
export const TAP_SLOP = 8;
// Press time before the NO / YES options appear (a plain tap does not flash them).
export const ENGAGE_AFTER_MS = 300;

// ---------- How far the card can go ----------
// Desktop: up to the NO / YES text (one card width + this gap; the same 56px gap is in index.css `.deck-slot`).
export const DESKTOP_GAP_PX = 56;
// Phone: this share of the card width (small, so the YES / NO text stays on screen; the decision still
// follows the finger, SWIPE_X), and the card size at full pull.
export const PHONE_DRAG_SHARE = 0.08;
export const PHONE_DRAG_SCALE = 0.92;
// How much the card stretches past the limit (0 = hard stop).
export const DRAG_ELASTIC = 0.03;

// ---------- Outcome preview while dragging ----------
// Drag distance at which the phone starts to swap the card for the outcome view.
export const PREVIEW_START = 25;
// Drag distance at which the outcome / background colour is at full strength.
export const PREVIEW_FULL_AT = 110;
// Gap between the NO and YES backgrounds in the middle of the stage (desktop).
export const BACKDROP_GAP = 16;

// ---------- Locked card (back not seen yet) ----------
// Sideways move that starts the "tap here" waves (swiping is possible only after the back was seen).
export const LOCK_NUDGE_X = 24;

// ---------- Idle help (timers restart on any tap or key press) ----------
// Before the first flip: no tap for this long → waves come out from under the card.
export const TAP_HINT_AFTER_MS = 7000;
// After the card was opened: every this long without action → the card sways left and right.
export const NUDGE_EVERY_MS = 8500;
// Sway size (kept under PREVIEW_START, so a phone does not switch to the outcome view) and duration.
export const NUDGE_X = 18;
export const NUDGE_DURATION_S = 1.1;

// ---------- Tap waves (CSS `tap-wave` / `tap-press` in index.css read these through CSS variables) ----------
// Waves per cycle, the delay between them, and the whole cycle (waves + pause).
export const WAVE_COUNT = 2;
export const WAVE_GAP_S = 0.8;
export const WAVE_CYCLE_S = 3.6;
// How far a wave travels from the card edge (about 1 cm at 96 dpi) and the card corner radius it starts from.
export const WAVE_REACH_PX = 34;
export const CARD_RADIUS_PX = 28;
// Card size when a wave leaves it (1% smaller).
export const WAVE_PRESS_SCALE = 0.99;
// Grey tone of the waves and the "Tap the card to see why" label (RGB, used with alpha in CSS).
export const WAVE_RGB = '107, 113, 108';
