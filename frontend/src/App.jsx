import React, { useCallback, useEffect, useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import AppLayout from './components/layout/AppLayout.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Analysis from './pages/Analysis.jsx';
import Invoices from './pages/Invoices.jsx';
import Risk from './pages/Risk.jsx';
import Mail from './pages/Mail.jsx';
import ComingSoon from './pages/ComingSoon.jsx';
import History from './pages/History.jsx';
import Rules from './pages/Rules.jsx';
import Advisor from './pages/Advisor.jsx';
import DemoReset from './pages/DemoReset.jsx';
import Settings from './pages/Settings.jsx';
import LoginPage from './pages/LoginPage.jsx';
import { AppStateProvider } from './state/AppState.jsx';
import { fetchCurrentUser } from './api/authApi.js';
import { clearToken, setUnauthorizedHandler } from './api/client.js';
import { HTTP_UNAUTHORIZED } from './const/api.js';

export default function App() {
  const [user, setUser] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [sessionError, setSessionError] = useState('');

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null));
    return () => setUnauthorizedHandler(null);
  }, []);

  const checkSession = useCallback(() => {
    setCheckingSession(true);
    setSessionError('');

    fetchCurrentUser()
      .then(setUser)
      .catch((err) => {
        setUser(null);
        if (err.status !== HTTP_UNAUTHORIZED) setSessionError(err.message);
      })
      .finally(() => setCheckingSession(false));
  }, []);

  useEffect(checkSession, [checkSession]);

  const handleLogout = () => {
    clearToken();
    setUser(null);
  };

  if (checkingSession) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
      </div>
    );
  }

  if (sessionError) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center space-y-3">
        <p className="text-sm text-slate-700">Cannot reach the server: {sessionError}</p>
        <button
          type="button"
          onClick={checkSession}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!user) {
    return <LoginPage onAuthenticated={setUser} />;
  }

  return (
    <AppStateProvider>
      <Routes>
        <Route element={<AppLayout onLogout={handleLogout} />}>
          <Route index element={<Dashboard />} />
          <Route path="analysis" element={<Analysis />} />
          <Route path="invoices" element={<Invoices />} />
          <Route path="risk" element={<Risk />} />
          <Route path="mail" element={<Mail />} />
          <Route path="advisor" element={<Advisor />} />
          <Route path="history" element={<History />} />
          <Route path="ledger" element={<Navigate to="/history" replace />} />
          <Route path="rules" element={<Rules />} />
          <Route path="settings" element={<Settings />} />
          <Route path="demo-reset" element={<DemoReset />} />
          <Route path="*" element={<ComingSoon title="Page not found" text="This page does not exist." />} />
        </Route>
      </Routes>
    </AppStateProvider>
  );
}
