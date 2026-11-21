import { useCallback, useEffect, useMemo, useState } from 'react';
import { listActions, updateActionStatus } from '../api/actionApi.js';
import { getForecast, previewAction } from '../api/forecastApi.js';
import { ACTION_STATUS, DECIDED_ACTION_STATUSES } from '../const/api.js';
import { DEFAULT_FORECAST_HORIZON } from '../const/forecast.js';

export function useForecastDeck() {
  const [horizon, setHorizon] = useState(DEFAULT_FORECAST_HORIZON);
  const [forecast, setForecast] = useState(null);
  const [cards, setCards] = useState([]);
  const [preview, setPreview] = useState(null);
  const [busyCardId, setBusyCardId] = useState(null);
  const [error, setError] = useState('');

  const pending = useMemo(() => cards.filter((card) => card.status === ACTION_STATUS.pending), [cards]);
  const decided = useMemo(() => cards.filter((card) => DECIDED_ACTION_STATUSES.includes(card.status)), [cards]);
  const current = pending[0] || null;
  const currentId = current?.id;

  const reload = useCallback(async () => {
    const [nextForecast, nextCards] = await Promise.all([getForecast(horizon), listActions()]);
    setForecast(nextForecast);
    setCards(nextCards);
  }, [horizon]);

  useEffect(() => {
    reload().catch((err) => setError(err.message));
  }, [reload]);

  useEffect(() => {
    if (!currentId) {
      setPreview(null);
      return undefined;
    }

    let cancelled = false;
    setPreview(null);
    previewAction(currentId, horizon)
      .then((result) => !cancelled && setPreview(result))
      .catch(() => !cancelled && setPreview(null));

    return () => {
      cancelled = true;
    };
  }, [currentId, horizon, forecast]);

  const changeStatus = useCallback(
    async (cardId, status) => {
      setBusyCardId(cardId);
      setError('');

      try {
        await updateActionStatus(cardId, { status });
        await reload();
      } catch (err) {
        setError(err.message);
      } finally {
        setBusyCardId(null);
      }
    },
    [reload],
  );

  return {
    horizon,
    setHorizon,
    forecast,
    pending,
    decided,
    current,
    preview,
    busyCardId,
    error,
    approve: (cardId) => changeStatus(cardId, ACTION_STATUS.approved),
    reject: (cardId) => changeStatus(cardId, ACTION_STATUS.rejected),
    undo: (cardId) => changeStatus(cardId, ACTION_STATUS.pending),
  };
}
