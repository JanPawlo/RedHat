import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, TriangleAlert } from 'lucide-react';
import { Button, IconCircle, PageHeader } from '../components/ui/primitives.jsx';
import { resetDemo } from '../api/demoApi.js';

const LOCAL_STATE_PREFIX = 'redcaps.';

function clearLocalState() {
  try {
    Object.keys(localStorage)
      .filter((key) => key.startsWith(LOCAL_STATE_PREFIX))
      .forEach((key) => localStorage.removeItem(key));
  } catch {
    return;
  }
}

export default function DemoReset() {
  const navigate = useNavigate();
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');

  const confirm = async () => {
    setStatus('working');
    setError('');

    try {
      await resetDemo();
      clearLocalState();
      window.location.assign('/');
    } catch (err) {
      setStatus('idle');
      setError(err.message);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Demo reset" />
      <div className="card flex flex-col items-center gap-4 py-16 text-center">
        <IconCircle icon={TriangleAlert} size={72} />
        <p className="t-title">Warning: this resets all data</p>
        <p className="max-w-md t-body text-text-muted">
          The company data, bank transactions, invoices and every decision on the cards go back to the demo start state.
          Everyone testing right now sees the reset. User accounts stay.
        </p>
        <p className="t-body-m">Reset the data?</p>
        <div className="flex gap-3">
          <Button kind="soft" onClick={() => navigate(-1)} disabled={status === 'working'}>No</Button>
          <Button onClick={confirm} disabled={status === 'working'} icon={status === 'working' ? Loader2 : undefined}>
            {status === 'working' ? 'Resetting…' : 'Yes, reset'}
          </Button>
        </div>
        {error && <p className="t-small text-status-red">Reset failed: {error}</p>}
      </div>
    </div>
  );
}
