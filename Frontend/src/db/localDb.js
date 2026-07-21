import Dexie from 'dexie'

const db = new Dexie('PrevencionOfflineDB')

db.version(1).stores({
  // Cola de operaciones pendientes de sincronización
  // status: 'pending' | 'synced' | 'error'
  syncQueue: '++id, &uuid, endpoint, method, status, createdAt',

  // Cachés de entidades del negocio (para lectura sin conexión)
  prendas:     'sku, tipo_prenda, talla, empresa, disponible',
  personal:    'rut, nombre_completo, empresa, cargo',
  tipos:       'tipo_id, nombre_tipo',
  tallas:      'talla_id, nombre_talla',
})

export default db
