import React, { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Bell, CheckCheck, Info, Menu, Undo2, X } from 'lucide-react';
import Sidebar, { Logo, SidebarContent } from './Sidebar.jsx';
import { AlertsPanel } from '../dashboard/Alerts.jsx';
import Confirmation from '../confirmation/Confirmation.jsx';
import { useAppState } from '../../state/AppState.jsx';

function FeedbackToast() {
  const { toast, clearToast, undoLast } = useAppState();
  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(clearToast, 6000);
    return () => clearTimeout(t);
  }, [toast, clearToast]);

  return (
    <div className="pointer-events-none fixed inset-x-3 bottom-[max(16px,env(safe-area-inset-bottom))] z-50 flex justify-center sm:bottom-6">
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.key}
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ type: 'spring', stiffness: 420, damping: 32 }}
            className="pointer-events-auto flex max-w-full items-center gap-3 rounded-full bg-green-900 py-2 pl-4 pr-2 text-white shadow-card"
            role="status"
          >
            {toast.tone === 'green' ? <CheckCheck className="h-4 w-4 shrink-0 text-green-200" /> : <Info className="h-4 w-4 shrink-0 text-green-200" />}
            <span className="min-w-0 t-small">{toast.text}</span>
            {toast.undo && (
              <button type="button" onClick={undoLast} className="flex shrink-0 items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5 t-small hover:bg-white/20">
                <Undo2 className="h-3.5 w-3.5" /> Undo
              </button>
            )}
            <button type="button" onClick={clearToast} aria-label="Close" className="shrink-0 rounded-full p-1.5 text-green-200 hover:bg-white/10">
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** Phone and tablet: top bar with a hamburger that opens the menu as a drawer. */
function MobileHeader({ onMenu }) {
  const { alerts, setAlertsOpen } = useAppState();
  const unread = alerts.filter((a) => a.unread).length;
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 bg-canvas/95 px-4 backdrop-blur lg:hidden">
      <button type="button" onClick={onMenu} aria-label="Open menu" className="-ml-2 flex h-11 w-11 items-center justify-center rounded-full hover:bg-surface">
        <Menu className="h-6 w-6" />
      </button>
      <span className="flex min-w-0 flex-1 items-center gap-2">
        <Logo size={30} />
        <span className="truncate t-title">RedCaps CFO</span>
      </span>
      <button type="button" onClick={() => setAlertsOpen(true)} aria-label={unread ? `Notifications · ${unread} new` : 'Notifications'} className="relative -mr-2 flex h-11 w-11 items-center justify-center rounded-full hover:bg-surface">
        <Bell className="h-5 w-5" strokeWidth={1.8} />
        {unread > 0 && (
          <span className="absolute right-1 top-1 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-status-red px-1 text-[10px] font-semibold text-white ring-2 ring-canvas">{unread}</span>
        )}
      </button>
    </header>
  );
}

function Drawer({ open, onClose, onLogout }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
          <motion.div className="absolute inset-0 bg-ink/40" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} />
          <motion.aside
            className="absolute inset-y-0 left-0 flex w-[min(300px,86vw)] flex-col overflow-y-auto bg-surface px-4 pb-[max(16px,env(safe-area-inset-bottom))] pt-4 shadow-card"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', stiffness: 380, damping: 36 }}
          >
            <button type="button" onClick={onClose} aria-label="Close menu" className="absolute right-2 top-2.5 z-10 flex h-11 w-11 items-center justify-center rounded-full hover:bg-subtle">
              <X className="h-5 w-5" />
            </button>
            <SidebarContent onLogout={onLogout} onNavigate={onClose} />
          </motion.aside>
        </div>
      )}
    </AnimatePresence>
  );
}

export default function AppLayout({ onLogout }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const { alertsOpen, setAlertsOpen } = useAppState();
  const { pathname } = useLocation();

  useEffect(() => setMenuOpen(false), [pathname]);

  return (
    <div className="min-h-[100dvh] overflow-x-clip bg-canvas lg:flex lg:gap-6 lg:p-6">
      <Sidebar onLogout={onLogout} />
      <MobileHeader onMenu={() => setMenuOpen(true)} />
      <main className="min-w-0 flex-1 px-4 pb-6 pt-2 lg:p-0">
        <Outlet />
      </main>
      <Drawer open={menuOpen} onClose={() => setMenuOpen(false)} onLogout={onLogout} />
      <AlertsPanel open={alertsOpen} onClose={() => setAlertsOpen(false)} />
      <Confirmation />
      <FeedbackToast />
    </div>
  );
}
