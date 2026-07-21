import { useState, useEffect } from 'react'
import { getPendingCount } from '../sync/syncManager'

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [pendingCount, setPendingCount] = useState(0)

  // Actualizar count inicial y después de cada sync
  useEffect(() => {
    getPendingCount().then(setPendingCount)

    const onOnline  = () => setIsOnline(true)
    const onOffline = () => setIsOnline(false)
    const onSync    = async () => setPendingCount(await getPendingCount())

    window.addEventListener('online',               onOnline)
    window.addEventListener('offline',              onOffline)
    window.addEventListener('civot:sync-complete',  onSync)

    return () => {
      window.removeEventListener('online',              onOnline)
      window.removeEventListener('offline',             onOffline)
      window.removeEventListener('civot:sync-complete', onSync)
    }
  }, [])

  return { isOnline, pendingCount }
}
