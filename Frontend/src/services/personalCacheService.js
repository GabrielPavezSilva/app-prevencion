import { apiClient } from './api'
import db from '../db/localDb'

export async function poblarCachePersonal() {
  if (!navigator.onLine) return
  try {
    const data = await apiClient.get('/personal/todos')
    const lista = Array.isArray(data) ? data : (data?.data ?? [])
    if (lista.length > 0) {
      await db.personal.bulkPut(lista)
    }
  } catch {
    // caché best-effort: si falla, no interrumpe el arranque
  }
}

export async function buscarPersonalOffline(searchTerm) {
  if (!searchTerm) return []
  const term = searchTerm.toLowerCase().replace(/[.-]/g, '')
  const todos = await db.personal.toArray()
  return todos.filter((p) => {
    const nombre = (p.nombre_completo || '').toLowerCase()
    const rut = (p.rut || '').replace(/[.-]/g, '').toLowerCase()
    return nombre.includes(term) || rut.includes(term)
  })
}
