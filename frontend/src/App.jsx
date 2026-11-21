import React, { useCallback, useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import Dashboard from './pages/Dashboard.jsx';
import LoginPage from './pages/LoginPage.jsx';
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

  return <Dashboard user={user} onLogout={handleLogout} />;
}
