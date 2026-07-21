import { useState, useEffect } from 'react'
import { useOnlineStatus } from '../hooks/useOnlineStatus'

const SYNC_BADGE_DURATION_MS = 3500

export default function OfflineBanner() {
  const { isOnline, pendingCount } = useOnlineStatus()
  const [showSyncBadge, setShowSyncBadge] = useState(false)

  // Mostrar badge verde brevemente después de cada sincronización exitosa
  useEffect(() => {
    const handler = (e) => {
      if (e.detail?.synced > 0) {
        setShowSyncBadge(true)
        const t = setTimeout(() => setShowSyncBadge(false), SYNC_BADGE_DURATION_MS)
        return () => clearTimeout(t)
      }
    }
    window.addEventListener('civot:sync-complete', handler)
    return () => window.removeEventListener('civot:sync-complete', handler)
  }, [])

  if (!isOnline) {
    return (
      <div style={styles.offline}>
        <span style={styles.icon}>⚠️</span>
        <span>
          Sin conexión — Los cambios se guardarán y sincronizarán al reconectar
          {pendingCount > 0 && (
            <strong style={styles.count}> ({pendingCount} pendiente{pendingCount !== 1 ? 's' : ''})</strong>
          )}
        </span>
      </div>
    )
  }

  if (showSyncBadge) {
    return (
      <div style={styles.synced}>
        <span style={styles.icon}>✓</span>
        <span>Datos sincronizados</span>
      </div>
    )
  }

  // Online sin badge — mostrar contador si queda algo pendiente
  if (pendingCount > 0) {
    return (
      <div style={styles.pending}>
        <span style={styles.icon}>↑</span>
        <span>Sincronizando {pendingCount} operación{pendingCount !== 1 ? 'es' : ''}…</span>
      </div>
    )
  }

  return null
}

const base = {
  position: 'fixed',
  bottom: '72px',        // encima del área donde react-hot-toast aparece
  left: '50%',
  transform: 'translateX(-50%)',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  padding: '10px 20px',
  borderRadius: '8px',
  fontSize: '0.85rem',
  fontFamily: 'var(--font-family, "Inter", sans-serif)',
  fontWeight: 500,
  zIndex: 9999,
  boxShadow: '0 4px 12px rgba(0,0,0,0.35)',
  whiteSpace: 'nowrap',
  pointerEvents: 'none',
}

const styles = {
  offline: {
    ...base,
    background: '#854d0e',
    color: '#fef9c3',
    border: '1px solid #a16207',
  },
  synced: {
    ...base,
    background: '#14532d',
    color: '#dcfce7',
    border: '1px solid #16a34a',
  },
  pending: {
    ...base,
    background: '#1e3a5f',
    color: '#bfdbfe',
    border: '1px solid #3b82f6',
  },
  icon: { fontSize: '1rem' },
  count: { marginLeft: 4 },
}
