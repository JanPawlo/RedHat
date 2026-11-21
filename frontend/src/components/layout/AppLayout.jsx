import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCheck, Info, Undo2, X } from 'lucide-react';
import Sidebar from './Sidebar.jsx';
import { useAppState } from '../../state/AppState.jsx';

function FeedbackToast() {
  const { toast, clearToast, undoLast } = useAppState();
  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(clearToast, 6000);
    return () => clearTimeout(t);
  }, [toast, clearToast]);

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex justify-center">
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.key}
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ type: 'spring', stiffness: 420, damping: 32 }}
            className="pointer-events-auto flex items-center gap-3 rounded-full bg-green-900 py-2 pl-4 pr-2 text-white shadow-card"
            role="status"
          >
            {toast.tone === 'green' ? <CheckCheck className="h-4 w-4 text-green-200" /> : <Info className="h-4 w-4 text-green-200" />}
            <span className="t-small">{toast.text}</span>
            {toast.undo && (
              <button type="button" onClick={undoLast} className="flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5 t-small hover:bg-white/20">
                <Undo2 className="h-3.5 w-3.5" /> Undo
              </button>
            )}
            <button type="button" onClick={clearToast} aria-label="Close" className="rounded-full p-1.5 text-green-200 hover:bg-white/10">
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function AppLayout({ onLogout }) {
  return (
    <div className="flex min-h-screen gap-6 bg-canvas p-6">
      <Sidebar onLogout={onLogout} />
      <main className="min-w-0 flex-1">
        <Outlet />
      </main>
      <FeedbackToast />
    </div>
  );
}
