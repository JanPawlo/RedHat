import React, { useState } from 'react';
import { Lock, Mail, User, Loader2 } from 'lucide-react';
import { login, register } from '../api/authApi.js';

export default function LoginPage({ onAuthenticated }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const isRegister = mode === 'register';

  const switchMode = () => {
    setMode(isRegister ? 'login' : 'register');
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = isRegister
        ? await register(email, password, fullName)
        : await login(email, password);
      onAuthenticated(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center space-x-3 mb-8">
          <div className="bg-indigo-600 text-white p-2 rounded-lg font-bold">CFO</div>
          <div>
            <h1 className="text-lg font-semibold text-slate-800">Autonomous CFO Agent</h1>
            <p className="text-xs text-slate-500">Commerzbank &bull; Red Hat Collabothon 2026</p>
          </div>
        </div>

        <div className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">
            {isRegister ? 'Create an account' : 'Sign in'}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {isRegister
              ? 'Register to start managing your liquidity with the CFO agent.'
              : 'Welcome back. Sign in to your CFO dashboard.'}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            {isRegister && (
              <label className="block">
                <span className="text-sm font-medium text-slate-700">Full name</span>
                <div className="mt-1 relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    autoComplete="name"
                    className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Jane Doe"
                  />
                </div>
              </label>
            )}

            <label className="block">
              <span className="text-sm font-medium text-slate-700">{isRegister ? 'Email' : 'Email or login'}</span>
              <div className="mt-1 relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type={isRegister ? 'email' : 'text'}
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete={isRegister ? 'email' : 'username'}
                  className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder={isRegister ? 'you@company.com' : 'you@company.com or admin'}
                />
              </div>
            </label>

            <label className="block">
              <span className="text-sm font-medium text-slate-700">Password</span>
              <div className="mt-1 relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  minLength={isRegister ? 8 : 1}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={isRegister ? 'new-password' : 'current-password'}
                  className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  placeholder={isRegister ? 'At least 8 characters' : '••••••••'}
                />
              </div>
            </label>

            {error && (
              <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-semibold rounded-lg shadow-sm"
            >
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {isRegister ? 'Create account' : 'Sign in'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button type="button" onClick={switchMode} className="font-semibold text-indigo-600 hover:text-indigo-700">
              {isRegister ? 'Sign in' : 'Register'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
