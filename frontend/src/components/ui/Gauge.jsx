import React from 'react';

/**
 * Half-circle gauge. Either one value (`pct`, 0–100) or colored `segments` [[from, to, color], …]
 * with a `marker` (0–1). Content passed as children sits in the middle.
 */
export default function Gauge({ pct = 0, size = 320, stroke = 26, segments, marker, children }) {
  const r = size / 2 - stroke;
  const cx = size / 2;
  const cy = size / 2;
  const point = (p) => [cx - r * Math.cos(Math.PI * p), cy - r * Math.sin(Math.PI * p)];
  const arc = (a, b) => {
    const [x1, y1] = point(a);
    const [x2, y2] = point(b);
    return `M${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}`;
  };
  const h = size / 2 + stroke / 2;
  const [mx, my] = marker != null ? point(marker) : [0, 0];
  return (
    <div className="relative mx-auto w-full" style={{ maxWidth: size, aspectRatio: `${size} / ${h}` }}>
      <svg viewBox={`0 0 ${size} ${h}`} className="h-full w-full overflow-visible" aria-hidden>
        {segments ? (
          segments.map(([a, b, color]) => <path key={a} d={arc(a, b)} stroke={color} strokeWidth={stroke - 4} fill="none" />)
        ) : (
          <>
            <path d={arc(0, 1)} stroke="#F5F4F0" strokeWidth={stroke} fill="none" strokeLinecap="round" />
            {pct > 0 && <path d={arc(0, pct / 100)} stroke="#3F5E4A" strokeWidth={stroke} fill="none" strokeLinecap="round" />}
          </>
        )}
        {marker != null && <circle cx={mx} cy={my} r={12} fill="#fff" stroke="#23382B" strokeWidth={5} />}
      </svg>
      <div className="absolute inset-x-0 bottom-0 flex flex-col items-center">{children}</div>
    </div>
  );
}
