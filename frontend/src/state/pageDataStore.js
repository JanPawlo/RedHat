import { useEffect, useState } from 'react';

const cache = new Map();

/** Page data from the database, asked again on every visit (decisions change it); the last answer or `fallback` meanwhile. */
export function usePageData(key, loader, fallback) {
  const [data, setData] = useState(() => cache.get(key) ?? null);

  useEffect(() => {
    let active = true;
    loader()
      .then((next) => {
        cache.set(key, next);
        if (active) setData(next);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [key, loader]);

  return data || fallback;
}
