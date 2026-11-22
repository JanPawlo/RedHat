/**
 * Pass as `onUpdate` to a motion component to keep its animations on framer-motion's own frame loop.
 *
 * Without it, framer-motion 11 runs opacity / transform animations as browser (WAAPI) animations. When one
 * finishes, there is one frame where the browser animation is gone but framer has not written the final value
 * yet, so the element shows its old value: an opened panel blinks to opacity 0, a closing one blinks back to 1.
 * framer-motion never accelerates an element that has `onUpdate`, so this no-op removes that frame.
 */
export function keepOnMainThread() {}
