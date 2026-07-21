/**
 * Sync Manager — procesa la cola de operaciones offline secuencialmente.
 *
 * Estrategia:
 * - Al montar la app (iniciarSyncManager) y cada vez que el navegador recupera red,
 *   se llama a procesarCola().
 * - Los registros se procesan en orden createdAt ASC para preservar secuencia.
 * - Éxito (2xx): status → 'synced'.
 * - Error: retries++; si retries >= 3 → status 'error' (no reintenta más).
 * - Al terminar emite evento custom `civot:sync-complete` con { synced, errors }.
 */
import { apiClient } from '../services/api'
import db from '../db/localDb'

const MAX_RETRIES = 3

async function _ejecutarItem(item) {
  const payload = JSON.parse(item.payload)
  const headers = {
    'Content-Type': 'application/json',
    ...apiClient.headers,
  }

  const res = await fetch(`${apiClient.baseURL}${item.endpoint}`, {
    method: item.method,
    headers,
    body: item.method !== 'GET' ? JSON.stringify(payload) : undefined,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || body.message || `HTTP ${res.status}`)
  }

  return res.json().catch(() => ({}))
}

export async function procesarCola() {
  const pendientes = await db.syncQueue
    .where('status')
    .equals('pending')
    .sortBy('createdAt')

  if (pendientes.length === 0) return

  let synced = 0
  let errors = 0

  for (const item of pendientes) {
    try {
      await _ejecutarItem(item)
      await db.syncQueue.update(item.id, { status: 'synced' })
      synced++
    } catch {
      const nuevosRetries = (item.retries ?? 0) + 1
      const nuevoStatus = nuevosRetries >= MAX_RETRIES ? 'error' : 'pending'
      await db.syncQueue.update(item.id, { retries: nuevosRetries, status: nuevoStatus })
      if (nuevoStatus === 'error') errors++
    }
  }

  window.dispatchEvent(new CustomEvent('civot:sync-complete', { detail: { synced, errors } }))
}

export async function getPendingCount() {
  return db.syncQueue.where('status').equals('pending').count()
}

export async function reintentarErrores(ids) {
  if (ids && ids.length > 0) {
    await Promise.all(ids.map((id) => db.syncQueue.update(id, { status: 'pending', retries: 0 })))
  } else {
    await db.syncQueue.where('status').equals('error').modify({ status: 'pending', retries: 0 })
  }
  procesarCola()
}

export async function limpiarSincronizados() {
  await db.syncQueue.where('status').equals('synced').delete()
}

export function iniciarSyncManager() {
  // Al reconectar → sincronizar cola
  window.addEventListener('online', () => {
    procesarCola()
  })

  // Al iniciar, si ya hay red, sincronizar cola inmediatamente
  if (navigator.onLine) {
    procesarCola()
  }
}
