import React from 'react';
import { motion, useTransform } from 'framer-motion';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { cx } from '../../utils/format.js';
import { BACKDROP_GAP, PREVIEW_FULL_AT } from '../../const/cardMotion.js';


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
  // Phone (compact): the text sits on the side that stays on screen. NO slides left, so it is right-aligned; YES the other way.
  const toRight = compact && side === 'no';
  const items = !compact ? 'items-center' : toRight ? 'items-end' : 'items-start';
  const textAlign = !compact ? 'text-center' : toRight ? 'text-right' : 'text-left';

  return (
    <div className={cx('relative flex h-full w-full flex-col', items, textAlign, compact ? 'gap-3' : 'gap-4')}>
      <div className={cx('flex flex-1 flex-col justify-center gap-3', compact && 'w-full', items)}>
        <span className={cx('font-display font-black leading-none tracking-wide', s.text, compact ? 'text-[44px]' : 'text-[52px] xl:text-[60px]')}>{s.word}</span>
        <span className={cx('h-[3px] w-16 rounded-full', s.line)} aria-hidden />
        <span className="flex items-center gap-2 font-display text-[20px] font-bold leading-tight xl:text-[22px]">
          {side === 'no' && <IconCmp className={cx('h-5 w-5 shrink-0', s.text)} strokeWidth={2.4} />}
          {card[s.key]}
          {side === 'yes' && <IconCmp className={cx('h-5 w-5 shrink-0', s.text)} strokeWidth={2.4} />}
        </span>
        {outcomes.length > 0 && (
          <ul className={cx('mt-1 flex w-full max-w-[300px] flex-col gap-1.5', toRight ? 'text-right' : 'text-left')}>
            {outcomes.map((o) => (
              <li key={o} className={cx('flex items-start gap-2 rounded-xl px-3 py-2 t-small text-text', toRight && 'flex-row-reverse', s.soft)}>
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
 * Desktop: background of one half of the deck (NO left, YES right), a separate area with its own
 * rounded corners. Its color is strongest at the outer edge and fades to white toward the middle, and gets
 * stronger while the card is dragged toward it.
 */
export function DecisionBackdrop({ side, dragX, visible }) {
  const yes = side === 'yes';
  const strength = useTransform(dragX, yes ? [0, PREVIEW_FULL_AT] : [-PREVIEW_FULL_AT, 0], yes ? [0, 1] : [1, 0]);
  const half = `calc(50% - ${BACKDROP_GAP / 2}px)`;
  return (
    <motion.div
      aria-hidden
      initial={false}
      animate={{ opacity: visible ? 1 : 0 }}
      transition={{ duration: 0.25 }}
      style={{ width: half }}
      className={cx('pointer-events-none absolute inset-y-0 overflow-hidden rounded-card', yes ? 'right-0' : 'left-0')}
    >
      <div className={cx('absolute inset-0', yes ? 'bg-gradient-to-l from-status-green-soft to-white' : 'bg-gradient-to-r from-status-red-soft to-white')} />
      <motion.div
        style={{ opacity: strength }}
        className={cx('absolute inset-0', yes ? 'bg-gradient-to-l from-status-green/25 to-white/0' : 'bg-gradient-to-r from-status-red/25 to-white/0')}
      />
    </motion.div>
  );
}

/**
 * Desktop: the text of one decision beside the card (same size as the card). The background is
 * `DecisionBackdrop`; the text gets clearer while the card is dragged toward it.
 */
export function DecisionZone({ side, card, dragX, progress, armed, ready }) {
  const yes = side === 'yes';
  const strength = useTransform(dragX, yes ? [0, PREVIEW_FULL_AT] : [-PREVIEW_FULL_AT, 0], yes ? [0, 1] : [1, 0]);
  const contentOpacity = useTransform(strength, [0, 1], [0.55, 1]);

  return (
    <motion.div
      style={{ opacity: contentOpacity }}
      className="relative h-full w-full p-6 xl:p-8"
      aria-label={`${yes ? 'Yes' : 'No'}: ${card[yes ? 'right' : 'left']}`}
    >
      <OutcomeContent side={side} card={card} progress={progress} armed={armed} ready={ready} />
    </motion.div>
  );
}
