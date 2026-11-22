// Advisor page (notes, voice messages, meeting recordings + AI chat).
export const ADVISOR_STORAGE_KEY = 'redcaps.advisor.v2';

// Same limit as the backend `EXPLAIN_QUESTION_MAX_LENGTH`.
export const ADVISOR_QUESTION_MAX_LENGTH = 1000;
export const ADVISOR_NOTE_MAX_LENGTH = 2000;
export const ADVISOR_TITLE_MAX_LENGTH = 80;
// Earlier chat turns sent with a question (keeps the prompt small for the 8B model).
export const ADVISOR_HISTORY_TURNS = 6;
export const ADVISOR_MAX_RECORDING_MS = 3 * 60 * 1000;
export const ADVISOR_MAX_UPLOAD_MB = 200;

export const RESPONSE_SOURCE_BUSY_FALLBACK = 'busy_fallback';
// Shown above a refusal: which layer stopped the question, e.g. "Stopped by NeMo Guardrails: self check input".
export const GUARDRAIL_NOTE_PREFIX = 'Stopped by ';
// Wait before asking again when the backend says "busy" without a Retry-After.
export const AI_DEFAULT_RETRY_SECONDS = 5;

export const MATERIAL_KIND = {
  note: 'note',
  voice: 'voice',
  meeting: 'meeting',
};

export const ADVISOR_MESSAGES = {
  modelOffline: 'Could not reach the model on OpenShift AI. Try again in a moment.',
  modelBusy: 'The model on OpenShift AI is busy answering other questions. Try again in a few seconds.',
  busyFallback: 'Model busy · numbers straight from the forecast engine',
  micBlocked: 'The microphone is blocked. Allow it in the browser to record a voice message.',
  micMissing: 'This browser cannot record audio.',
  fileTooBig: `The file is larger than ${ADVISOR_MAX_UPLOAD_MB} MB.`,
  noTranscript: 'Automatic transcription is not connected yet. Add the key points so the agent can use them.',
};
