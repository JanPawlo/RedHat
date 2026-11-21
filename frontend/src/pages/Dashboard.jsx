import React, { useEffect, useState } from 'react';
import { TrendingUp, AlertTriangle, Bot, LogOut } from 'lucide-react';
import { listAccounts } from '../api/accountApi.js';
import { listActions, updateActionStatus } from '../api/actionApi.js';
import { getCompanyProfile } from '../api/companyApi.js';
import { checkHealth } from '../api/healthApi.js';
import { ACTION_STATUS, API_STATUS } from '../const/api.js';
import { DEFAULT_CURRENCY, MONEY_LOCALE } from '../const/format.js';

function formatMoney(amount, currency = DEFAULT_CURRENCY) {
  return new Intl.NumberFormat(MONEY_LOCALE, { style: 'currency', currency }).format(Number(amount));
}

function getLiquidityStatus(account, company) {
  const buffer = company?.settings?.min_safety_buffer;
  if (!account || buffer === undefined) return null;

  return {
    isSafe: Number(account.current_balance) >= Number(buffer),
    buffer,
  };
}

export default function Dashboard({ user, onLogout }) {
  const [apiStatus, setApiStatus] = useState(API_STATUS.checking);
  const [company, setCompany] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [pendingActions, setPendingActions] = useState([]);
  const [error, setError] = useState('');
  const [busyActionId, setBusyActionId] = useState(null);

  useEffect(() => {
    checkHealth()
      .then(() => setApiStatus(API_STATUS.connected))
      .catch(() => setApiStatus(API_STATUS.offline));
  }, []);

  useEffect(() => {
    Promise.all([
      getCompanyProfile().catch(() => null),
      listAccounts(),
      listActions({ status: ACTION_STATUS.pending }),
    ])
      .then(([profile, accountList, actionList]) => {
        setCompany(profile);
        setAccounts(accountList);
        setPendingActions(actionList);
      })
      .catch((err) => setError(err.message));
  }, []);

  const decide = async (actionId, status) => {
    setBusyActionId(actionId);
    setError('');

    try {
      await updateActionStatus(actionId, { status });
      setPendingActions((actions) => actions.filter((action) => action.id !== actionId));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyActionId(null);
    }
  };

  const primaryAccount = accounts[0];
  const liquidity = getLiquidityStatus(primaryAccount, company);
  const nextAction = pendingActions[0];

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-indigo-600 text-white p-2 rounded-lg font-bold">CFO</div>
          <div>
            <h1 className="text-lg font-semibold text-slate-800">Autonomous CFO Agent</h1>
            <p className="text-xs text-slate-500">Commerzbank &bull; Red Hat Collabothon 2026</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {company && (
            <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
              Profile: {company.name}
            </span>
          )}
          <div className="flex items-center space-x-1.5 text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                apiStatus === API_STATUS.connected ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
            <span className="text-slate-500 capitalize">{apiStatus}</span>
          </div>
          <span className="text-xs text-slate-600">{user?.full_name || user?.email}</span>
          <button
            type="button"
            onClick={onLogout}
            className="flex items-center text-xs font-medium px-2.5 py-1 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50"
          >
            <LogOut className="w-3.5 h-3.5 mr-1" /> Log out
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{error}</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">Current Balance</span>
              {primaryAccount && (
                <span className="p-2 bg-emerald-50 text-emerald-600 rounded-lg text-xs">{primaryAccount.bank_name}</span>
              )}
            </div>
            <div className="mt-4 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-slate-900">
                {primaryAccount ? formatMoney(primaryAccount.current_balance, primaryAccount.currency) : '—'}
              </span>
              <span className="text-xs text-slate-500">{primaryAccount?.account_name || 'No bank account yet'}</span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">Safety Buffer</span>
              <TrendingUp className="w-4 h-4 text-slate-400" />
            </div>
            <div className="mt-4 flex items-baseline justify-between">
              {liquidity ? (
                <>
                  <span className={`text-2xl font-bold ${liquidity.isSafe ? 'text-indigo-600' : 'text-red-600'}`}>
                    {liquidity.isSafe ? 'Above buffer' : 'Below buffer'}
                  </span>
                  <span className="text-xs text-slate-500">Buffer: {formatMoney(liquidity.buffer)}</span>
                </>
              ) : (
                <span className="text-2xl font-bold text-slate-400">—</span>
              )}
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">Agent Action Required</span>
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            </div>
            <div className="mt-4 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-amber-600">
                {pendingActions.length} {pendingActions.length === 1 ? 'Recommendation' : 'Recommendations'}
              </span>
              <span className="text-xs text-slate-500">Human-in-the-loop</span>
            </div>
          </div>
        </div>

        {nextAction && (
          <div className="bg-gradient-to-r from-indigo-50 to-white p-6 rounded-xl border border-indigo-100 shadow-sm">
            <div className="flex items-start space-x-4">
              <div className="p-3 bg-indigo-600 text-white rounded-xl">
                <Bot className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold text-slate-900">{nextAction.title}</h3>
                  <span className="text-xs bg-amber-100 text-amber-800 font-medium px-2 py-0.5 rounded">
                    Action Required
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-600">{nextAction.trigger_reason}</p>
                <p className="mt-2 text-sm text-slate-600">{nextAction.explanation}</p>
                {nextAction.target_amount != null && (
                  <p className="mt-2 text-xs text-slate-500">
                    Amount: {formatMoney(nextAction.target_amount, nextAction.currency)} &bull; {nextAction.execution_mode}
                  </p>
                )}
                <div className="mt-4 flex items-center space-x-3">
                  <button
                    type="button"
                    disabled={busyActionId === nextAction.id}
                    onClick={() => decide(nextAction.id, ACTION_STATUS.approved)}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-xs font-semibold rounded-lg shadow-sm"
                  >
                    Approve
                  </button>
                  <button
                    type="button"
                    disabled={busyActionId === nextAction.id}
                    onClick={() => decide(nextAction.id, ACTION_STATUS.rejected)}
                    className="px-4 py-2 bg-white hover:bg-slate-50 disabled:opacity-60 text-slate-700 border border-slate-300 text-xs font-semibold rounded-lg"
                  >
                    Reject
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h2 className="text-base font-semibold text-slate-800 mb-2">Daily Liquidity & Forecast</h2>
          <p className="text-xs text-slate-500 mb-6">The forecast chart is not built yet.</p>
          <div className="h-64 border-2 border-dashed border-slate-200 rounded-lg flex items-center justify-center text-slate-400 text-sm">
            Cash Flow / Recharts Chart Component will render here
          </div>
        </div>
      </main>
    </div>
  );
}
