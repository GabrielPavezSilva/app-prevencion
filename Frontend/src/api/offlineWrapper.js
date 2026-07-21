/**
 * Wrapper sobre apiClient que implementa offline-first para operaciones de escritura.
 *
 * - POST/PATCH/DELETE: si hay conexión intenta el fetch real; si falla (o no hay red),
 *   encola en IndexedDB con status 'pending'. Retorna el payload con `_offline: true`
 *   cuando la operación queda en cola (optimistic UI).
 * - GET: intenta fetch real; acepta un fallback function para leer desde caché local.
 * - Cada operación lleva un UUID v4 generado en el cliente para garantizar idempotencia
 *   cuando el backend reintenta la sincronización.
 */
import { v4 as uuidv4 } from 'uuid'
import { apiClient } from '../services/api'
import db from '../db/localDb'

async function _enqueue(endpoint, method, payload) {
  await db.syncQueue.add({
    uuid: payload.uuid,
    endpoint,
    method,
    payload: JSON.stringify(payload),
    status: 'pending',
    retries: 0,
    createdAt: new Date().toISOString(),
  })
}

/**
 * Realiza un POST. Si offline o si el servidor falla, encola en syncQueue.
 * Retorna la respuesta del servidor o `{ ...payload, _offline: true }`.
 */
export async function apiPost(endpoint, payload = {}) {
  const enriched = { ...payload, uuid: payload.uuid ?? uuidv4() }

  if (!navigator.onLine) {
    await _enqueue(endpoint, 'POST', enriched)
    return { ...enriched, _offline: true }
  }

  try {
    return await apiClient.post(endpoint, enriched)
  } catch {
    await _enqueue(endpoint, 'POST', enriched)
    return { ...enriched, _offline: true }
  }
}

/**
 * Realiza un PATCH. El UUID se pasa en el body para idempotencia en el backend.
 */
export async function apiPatch(endpoint, payload = {}) {
  const enriched = { ...payload, uuid: payload.uuid ?? uuidv4() }

  if (!navigator.onLine) {
    await _enqueue(endpoint, 'PATCH', enriched)
    return { ...enriched, _offline: true }
  }

  try {
    return await apiClient.patch(endpoint, enriched)
  } catch {
    await _enqueue(endpoint, 'PATCH', enriched)
    return { ...enriched, _offline: true }
  }
}

/**
 * Realiza un DELETE. El UUID se incluye en el body para rastreo.
 * `payload` puede estar vacío — se genera el UUID de todas formas.
 */
export async function apiDelete(endpoint, payload = {}) {
  const enriched = { ...payload, uuid: payload.uuid ?? uuidv4() }

  if (!navigator.onLine) {
    await _enqueue(endpoint, 'DELETE', enriched)
    return { ...enriched, _offline: true }
  }

  try {
    return await apiClient.delete(endpoint, { body: JSON.stringify(enriched) })
  } catch {
    await _enqueue(endpoint, 'DELETE', enriched)
    return { ...enriched, _offline: true }
  }
}

/**
 * GET con fallback a caché local.
 * `fallbackFn` es una función async que devuelve datos desde IndexedDB cuando la
 * red no está disponible o el servidor no responde.
 *
 * Los GETs normales siguen yendo directo a apiClient (Workbox los cachea).
 */
export async function apiGet(endpoint, fallbackFn = null) {
  try {
    return await apiClient.get(endpoint)
  } catch (err) {
    if (fallbackFn) return fallbackFn()
    throw err
  }
}
