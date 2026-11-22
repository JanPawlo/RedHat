import { useCallback } from 'react';
import { useAppState } from '../state/AppState.jsx';
import { MOCKUP_NOTICE } from '../const/mockup.js';

/** Click handler for buttons that are only designed so far: shows a short "mock-up" note at the bottom. */
export function useMockupNotice() {
  const { showToast } = useAppState();
  return useCallback(() => showToast({ tone: 'neutral', text: MOCKUP_NOTICE }), [showToast]);
}
