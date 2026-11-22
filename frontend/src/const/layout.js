// Breakpoints used in JS; keep in line with Tailwind's screens.
export const DESKTOP_QUERY = '(min-width: 1024px)';

// Sidebar badge of the model on OpenShift AI (GET /ai/health; NeMo Guardrails status when it is on).
export const AI_HEALTH_ENDPOINT = '/ai/health';
export const NEMO_STATUS_CONNECTED = 'connected';
export const MODEL_BADGE_STATUS = {
  checking: 'checking',
  online: 'online',
  warning: 'warning',
  offline: 'offline',
};
export const MODEL_BADGE_TEXT = {
  defaultModel: 'Qwen3-8B · vLLM',
  checking: 'Checking model…',
  online: 'OpenShift AI · active',
  onlineGuarded: 'OpenShift AI · NeMo Guardrails on',
  warning: 'NeMo Guardrails unreachable',
  offline: 'Model offline · demo data',
  tooltip: 'Open-weights model served on Red Hat OpenShift AI',
};
