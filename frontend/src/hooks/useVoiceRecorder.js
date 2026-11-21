import { useCallback, useEffect, useRef, useState } from 'react';
import { ADVISOR_MAX_RECORDING_MS, ADVISOR_MESSAGES } from '../const/advisor.js';

const SpeechRecognition = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : undefined;

/**
 * Records a voice message with the microphone (MediaRecorder).
 * Where the browser supports it (Chrome, Edge, Safari), it also writes a live transcript.
 * Returns `{ status: 'idle' | 'recording' | 'done', seconds, audioUrl, transcript, error, start, stop, reset, setTranscript }`.
 */
export function useVoiceRecorder() {
  const [status, setStatus] = useState('idle');
  const [seconds, setSeconds] = useState(0);
  const [audioUrl, setAudioUrl] = useState(null);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState('');
  const recorder = useRef(null);
  const recognition = useRef(null);
  const timer = useRef(0);
  const limit = useRef(0);

  const cleanup = () => {
    clearInterval(timer.current);
    clearTimeout(limit.current);
    recognition.current?.stop?.();
    recognition.current = null;
  };

  const stop = useCallback(() => {
    if (recorder.current?.state === 'recording') recorder.current.stop();
    cleanup();
  }, []);

  const startTranscript = () => {
    if (!SpeechRecognition) return;
    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = navigator.language || 'en-GB';
    let finalText = '';
    rec.onresult = (e) => {
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i += 1) {
        const piece = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalText += `${piece} `;
        else interim += piece;
      }
      setTranscript(`${finalText}${interim}`.trim());
    };
    rec.onerror = () => {};
    try {
      rec.start();
      recognition.current = rec;
    } catch {
      /* transcript is optional */
    }
  };

  const start = useCallback(async () => {
    setError('');
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError(ADVISOR_MESSAGES.micMissing);
      return;
    }

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError(ADVISOR_MESSAGES.micBlocked);
      return;
    }

    const chunks = [];
    const rec = new MediaRecorder(stream);
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      setAudioUrl(URL.createObjectURL(new Blob(chunks, { type: rec.mimeType || 'audio/webm' })));
      setStatus('done');
    };
    recorder.current = rec;
    rec.start();

    setTranscript('');
    setSeconds(0);
    setStatus('recording');
    const startedAt = Date.now();
    timer.current = setInterval(() => setSeconds(Math.round((Date.now() - startedAt) / 1000)), 250);
    limit.current = setTimeout(stop, ADVISOR_MAX_RECORDING_MS);
    startTranscript();
  }, [stop]);

  const reset = useCallback(() => {
    cleanup();
    setStatus('idle');
    setSeconds(0);
    setAudioUrl(null);
    setTranscript('');
    setError('');
  }, []);

  useEffect(() => () => {
    cleanup();
    if (recorder.current?.state === 'recording') recorder.current.stop();
  }, []);

  return { status, seconds, audioUrl, transcript, setTranscript, error, start, stop, reset, canTranscribe: Boolean(SpeechRecognition) };
}
