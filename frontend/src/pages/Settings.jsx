import React, { useCallback, useEffect, useState } from 'react';
import { Landmark, Link2, Loader2, RefreshCw, Unlink } from 'lucide-react';
import { Button, Chip, IconCircle, PageHeader } from '../components/ui/primitives.jsx';
import { connectBank, disconnectBank, fetchBankConnections, syncBank } from '../api/bankApi.js';

const STATUS_CONNECTED = 'connected';

function formatMoney(value, currency) {
  try {
    return new Intl.NumberFormat('en-GB', { style: 'currency', currency }).format(Number(value));
  } catch {
    return `${value} ${currency}`;
  }
}

function formatDate(value) {
  return value ? new Date(value).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '—';
}

function formatDateTime(value) {
  return value ? new Date(value).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—';
}

function AccountRow({ account }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 rounded-2xl bg-subtle px-4 py-3">
      <div className="min-w-0">
        <p className="t-body-m">{account.account_name}</p>
        <p className="truncate t-small text-text-muted">{account.account_number} · {account.transactions} transactions</p>
      </div>
      <p className="t-body-m">{formatMoney(account.current_balance, account.currency)}</p>
    </li>
  );
}

function BankCard({ bank, busy, onConnect, onSync, onDisconnect }) {
  const connected = bank.status === STATUS_CONNECTED;

  return (
    <article className="card flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <IconCircle icon={Landmark} size={44} tone={connected ? 'green' : 'white'} />
        <div className="min-w-0 flex-1">
          <p className="t-title">{bank.name}</p>
          <p className="t-small text-text-muted">{bank.bic} · {bank.country}</p>
        </div>
        <Chip tone={connected ? 'green' : 'neutral'}>{connected ? 'Connected' : 'Not connected'}</Chip>
      </div>

      {connected && (
        <>
          <ul className="flex flex-col gap-2">
            {bank.accounts.map((account) => <AccountRow key={account.id} account={account} />)}
          </ul>
          <p className="t-small text-text-muted">
            Consent valid until {formatDate(bank.consent_valid_until)} · last sync {formatDateTime(bank.last_synced_at)}
          </p>
        </>
      )}

      <div className="flex flex-wrap gap-2">
        {connected ? (
          <>
            <Button kind="soft" size="sm" icon={busy ? Loader2 : RefreshCw} disabled={busy} onClick={onSync}>Sync now</Button>
            <Button kind="danger" size="sm" icon={Unlink} disabled={busy} onClick={onDisconnect}>Disconnect</Button>
          </>
        ) : (
          <Button size="sm" icon={busy ? Loader2 : Link2} disabled={busy} onClick={onConnect}>
            {busy ? 'Connecting…' : 'Connect'}
          </Button>
        )}
      </div>
    </article>
  );
}

export default function Settings() {
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyBank, setBusyBank] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setBanks(await fetchBankConnections());
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (bank, action, successText) => {
    setBusyBank(bank.id);
    setMessage('');
    setError('');

    try {
      const result = await action(bank.id);
      setMessage(successText(result));
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyBank(null);
    }
  };

  const connect = (bank) => run(bank, connectBank, () => `${bank.name} connected. Accounts and the last 60 days of transactions were imported.`);
  const sync = (bank) => run(bank, syncBank, (r) => `${bank.name} synced: ${r.imported} new, ${r.skipped} already known.`);
  const disconnect = (bank) => {
    if (!window.confirm(`Disconnect ${bank.name}? Its accounts and imported transactions will be removed.`)) return;
    run(bank, disconnectBank, () => `${bank.name} disconnected.`);
  };

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Settings" subtitle="Bank connections" />

      <section className="card flex flex-col gap-2">
        <p className="t-title">Connected banks (open banking)</p>
        <p className="t-body text-text-muted">
          Connect a bank instead of uploading CSV statements. The agent reads accounts, balances and transactions through a
          PSD2-style API. This is a demo: no real bank is contacted and the data is generated. Connected accounts are
          additional accounts; the forecast still uses the main operating account.
        </p>
      </section>

      {message && <p className="t-small text-status-green">{message}</p>}
      {error && <p className="t-small text-status-red">{error}</p>}

      {loading ? (
        <div className="flex items-center gap-2 t-body text-text-muted">
          <Loader2 className="h-4 w-4 animate-spin" /> Loading banks…
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {banks.map((bank) => (
            <BankCard
              key={bank.id}
              bank={bank}
              busy={busyBank === bank.id}
              onConnect={() => connect(bank)}
              onSync={() => sync(bank)}
              onDisconnect={() => disconnect(bank)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
