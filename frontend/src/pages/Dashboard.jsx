import React, { useEffect, useState } from 'react';
import { Loader2, LogOut } from 'lucide-react';
import { getCompanyProfile } from '../api/companyApi.js';
import { checkHealth } from '../api/healthApi.js';
import DecisionDeck, { previewEffect } from '../components/forecast/DecisionDeck.jsx';
import ForecastChart from '../components/forecast/ForecastChart.jsx';
import IndicatorTiles from '../components/forecast/IndicatorTiles.jsx';
import { API_STATUS } from '../const/api.js';
import { useForecastDeck } from '../hooks/useForecastDeck.js';

function Header({ company, apiStatus, user, onLogout }) {
  return (
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
          <span className={`w-2 h-2 rounded-full ${apiStatus === API_STATUS.connected ? 'bg-emerald-500' : 'bg-amber-500'}`} />
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
  );
}

export default function Dashboard({ user, onLogout }) {
  const [apiStatus, setApiStatus] = useState(API_STATUS.checking);
  const [company, setCompany] = useState(null);
  const deck = useForecastDeck();
  const effect = previewEffect(deck.preview);

  useEffect(() => {
    checkHealth()
      .then(() => setApiStatus(API_STATUS.connected))
      .catch(() => setApiStatus(API_STATUS.offline));

    getCompanyProfile().then(setCompany).catch(() => setCompany(null));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <Header company={company} apiStatus={apiStatus} user={user} onLogout={onLogout} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {deck.error && (
          <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700">{deck.error}</div>
        )}

        {!deck.forecast ? (
          <div className="flex items-center justify-center py-24 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        ) : (
          <>
            <IndicatorTiles forecast={deck.forecast} />

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
              <div className="lg:col-span-3">
                <ForecastChart
                  forecast={deck.forecast}
                  preview={deck.preview}
                  previewRisky={Boolean(effect?.breachDate)}
                  horizon={deck.horizon}
                  onHorizonChange={deck.setHorizon}
                />
              </div>
              <div className="lg:col-span-2">
                <DecisionDeck
                  current={deck.current}
                  pending={deck.pending}
                  decided={deck.decided}
                  effect={effect}
                  busyCardId={deck.busyCardId}
                  onApprove={deck.approve}
                  onReject={deck.reject}
                  onUndo={deck.undo}
                />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
