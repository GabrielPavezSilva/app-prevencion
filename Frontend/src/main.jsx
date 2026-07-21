import React from 'react';
import ReactDOM from 'react-dom/client';
import { Toaster } from 'react-hot-toast';
import App from './App.jsx';
import { ThemeProvider } from './context/ThemeContext.jsx';
import { iniciarSyncManager } from './sync/syncManager.js';
import OfflineBanner from './components/OfflineBanner.jsx';
import { poblarCachePersonal } from './services/personalCacheService.js';

iniciarSyncManager();
poblarCachePersonal();
window.addEventListener('online', poblarCachePersonal);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
      <OfflineBanner />
      <Toaster
        position="bottom-right"
        toastOptions={{
          duration: 3500,
          style: {
            background: 'var(--color-card)',
            color: 'var(--color-text-primary)',
            border: '1px solid var(--color-card-border)',
            fontFamily: "'Inter', sans-serif",
            fontSize: '0.875rem',
          },
          success: { iconTheme: { primary: '#10b981', secondary: 'var(--color-card)' } },
          error: { iconTheme: { primary: '#ef4444', secondary: 'var(--color-card)' } },
        }}
      />
    </ThemeProvider>
  </React.StrictMode>,
);
