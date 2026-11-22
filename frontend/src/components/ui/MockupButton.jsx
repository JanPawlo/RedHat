import React from 'react';
import { Button } from './primitives.jsx';
import { useMockupNotice } from '../../hooks/useMockupNotice.js';
import { MOCKUP_NOTICE, MOCKUP_TAG } from '../../const/mockup.js';

/**
 * A button that is only designed so far. Always the same look (dashed outline, muted text, "(mock-up)" after the
 * label) so it is clear before the click; the click shows the short mock-up note.
 */
export default function MockupButton({ children, icon, className }) {
  const showNotice = useMockupNotice();

  return (
    <Button kind="mockup" icon={icon} onClick={showNotice} title={MOCKUP_NOTICE} className={className}>
      {children}
      <span className="text-[11px] opacity-80">{MOCKUP_TAG}</span>
    </Button>
  );
}
