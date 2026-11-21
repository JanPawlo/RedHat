import React from 'react';
import { motion, useTransform } from 'framer-motion';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { cx } from '../../utils/format.js';

// Drag distance (px) at which the preview is fully shown; matches the point where holding starts to count.
export const PREVIEW_FULL_AT = 110;

const SIDES = {
  yes: { word: 'YES', key: 'right', icon: ArrowRight, text: 'text-status-green', soft: 'bg-status-green-soft', bar: 'bg-status-green', line: 'bg-status-green/40' },
  no: { word: 'NO', key: 'left', icon: ArrowLeft, text: 'text-status-red', soft: 'bg-status-red-soft', bar: 'bg-status-red', line: 'bg-status-red/40' },
};

function holdHint(side, armed, ready) {
  if (ready) return 'Release to confirm';
  if (armed) return 'Keep holding…';
  return `Drag further ${side === 'yes' ? 'right' : 'left'} and hold`;
}

/**
 * What a decision leads to: YES / NO, the decision itself and its consequences, plus the hold progress.
 * Used inside the side zones (desktop) and as the card's face while it is dragged (phone).
 */
export function OutcomeContent({ side, card, progress, armed, ready, compact = false }) {
  const s = SIDES[side];
  const width = useTransform(progress, (p) => `${armed ? p * 100 : 0}%`);
  const outcomes = card.outcomes?.[s.key] || [];
  const IconCmp = s.icon;

  return (
    <div className={cx('relative flex h-full w-full flex-col items-center text-center', compact ? 'gap-3' : 'gap-4')}>
      <div className="flex flex-1 flex-col items-center justify-center gap-3">
        <span className={cx('font-display font-black leading-none tracking-wide', s.text, compact ? 'text-[44px]' : 'text-[52px] xl:text-[60px]')}>{s.word}</span>
        <span className={cx('h-[3px] w-16 rounded-full', s.line)} aria-hidden />
        <span className="flex items-center gap-2 font-display text-[20px] font-bold leading-tight xl:text-[22px]">
          {side === 'no' && <IconCmp className={cx('h-5 w-5 shrink-0', s.text)} strokeWidth={2.4} />}
          {card[s.key]}
          {side === 'yes' && <IconCmp className={cx('h-5 w-5 shrink-0', s.text)} strokeWidth={2.4} />}
        </span>
        {outcomes.length > 0 && (
          <ul className="mt-1 flex w-full max-w-[300px] flex-col gap-1.5 text-left">
            {outcomes.map((o) => (
              <li key={o} className={cx('flex items-start gap-2 rounded-xl px-3 py-2 t-small text-text', s.soft)}>
                <span className={cx('mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full', s.bar)} aria-hidden />
                {o}
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="flex w-full max-w-[300px] flex-col gap-1.5">
        <span className="relative h-1.5 w-full overflow-hidden rounded-full bg-text/10">
          <motion.span className={cx('absolute inset-y-0 left-0 rounded-full', s.bar)} style={{ width }} />
        </span>
        <span className={cx('t-small', ready ? cx('font-semibold', s.text) : 'text-text-muted')}>{holdHint(side, armed, ready)}</span>
      </div>
    </div>
  );
}

/**
 * Desktop: a frame beside the card, the same size as the card. Its colored gradient grows
 * while the card is dragged toward it (`dragX` is the card's horizontal offset).
 */
export function DecisionZone({ side, card, dragX, progress, armed, ready }) {
  const yes = side === 'yes';
  const glow = useTransform(dragX, yes ? [0, PREVIEW_FULL_AT] : [-PREVIEW_FULL_AT, 0], yes ? [0, 1] : [1, 0]);
  const contentOpacity = useTransform(glow, [0, 1], [0.55, 1]);

  return (
    <div
      className={cx(
        'relative h-full w-full overflow-hidden rounded-card bg-surface/40',
      )}
      aria-label={`${yes ? 'Yes' : 'No'}: ${card[yes ? 'right' : 'left']}`}
    >
      <motion.div
        aria-hidden
        style={{ opacity: glow }}
        className={cx(
          'pointer-events-none absolute inset-0',
          yes ? 'bg-gradient-to-l from-status-green/35 via-status-green/15 to-status-green/5' : 'bg-gradient-to-r from-status-red/35 via-status-red/15 to-status-red/5',
        )}
      />
      <motion.div style={{ opacity: contentOpacity }} className="relative h-full p-6 xl:p-8">
        <OutcomeContent side={side} card={card} progress={progress} armed={armed} ready={ready} />
      </motion.div>
    </div>
  );
}
