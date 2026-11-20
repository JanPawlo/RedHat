import React, { useState, useEffect } from 'react';
import { ShieldCheck, TrendingUp, AlertTriangle, ArrowUpRight, ArrowDownRight, Bot } from 'lucide-react';

export default function App() {
  const [apiStatus, setApiStatus] = useState('checking');

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then(() => setApiStatus('connected'))
      .catch(() => setApiStatus('offline'));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top Navigation */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-indigo-600 text-white p-2 rounded-lg font-bold">CFO</div>
          <div>
            <h1 className="text-lg font-semibold text-slate-800">Autonomous CFO Agent</h1>
            <p className="text-xs text-slate-500">Commerzbank &bull; Red Hat Collabothon 2026</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
            Profile: Pizzeria Amalfi
          </span>
          <div className="flex items-center space-x-1.5 text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                apiStatus === 'connected' ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
            />
            <span className="text-slate-500 capitalize">{apiStatus}</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">Current Balance</span>
              <span className="p-2 bg-emerald-50 text-emerald-600 rounded-lg text-xs">Commerzbank Account</span>
            </div>
            <div className="mt-4 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-slate-900">€ 33,266.35</span>
              <span className="flex items-center text-xs font-semibold text-emerald-600">
                <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" /> +12.4% vs last mo
              </span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">Liquidity Horizon (30d)</span>
              <TrendingUp className="w-4 h-4 text-slate-400" />
            </div>
            <div className="mt-4 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-indigo-600">Safe (Buffer OK)</span>
              <span className="text-xs text-slate-500">Next drop: Wages (28th)</span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-slate-500">Agent Action Required</span>
              <AlertTriangle className="w-4 h-4 text-amber-500" />
            </div>
            <div className="mt-4 flex items-baseline justify-between">
              <span className="text-2xl font-bold text-amber-600">1 Recommendation</span>
              <span className="text-xs text-slate-500">Human-in-the-loop</span>
            </div>
          </div>
        </div>

        {/* Explainable AI Action Card Preview */}
        <div className="bg-gradient-to-r from-indigo-50 to-white p-6 rounded-xl border border-indigo-100 shadow-sm">
          <div className="flex items-start space-x-4">
            <div className="p-3 bg-indigo-600 text-white rounded-xl">
              <Bot className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-slate-900">
                  Liquidity Guard: Forecasted June Cash Flow Gap
                </h3>
                <span className="text-xs bg-amber-100 text-amber-800 font-medium px-2 py-0.5 rounded">
                  Action Required
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-600">
                Based on planned 3-week seasonal summer closure, expected balance will dip to <strong>-€22,097.60</strong>.
                Recommended mitigation: activate a temporary Commerzbank revolving credit buffer of €25,000 by May 25.
              </p>
              <div className="mt-4 flex items-center space-x-3">
                <button className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm">
                  Simulate & Approve Limit
                </button>
                <button className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-semibold rounded-lg">
                  View Detailed Breakdown
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Chart / Data Placeholder */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h2 className="text-base font-semibold text-slate-800 mb-2">2025 Daily Liquidity & Forecast</h2>
          <p className="text-xs text-slate-500 mb-6">Historical data seeded from Pizzeria Amalfi bank statement.</p>
          <div className="h-64 border-2 border-dashed border-slate-200 rounded-lg flex items-center justify-center text-slate-400 text-sm">
            Cash Flow / Recharts Chart Component will render here
          </div>
        </div>
      </main>
    </div>
  );
}
