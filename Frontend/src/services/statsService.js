import { apiClient } from './api';

export const getStatsInventario = (filtros = {}) => {
    const params = new URLSearchParams();
    const { tipo_id, talla_id, empresa_id, seccion_id, temporada_id } = filtros;
    if (tipo_id      != null) params.append('tipo_id',      tipo_id);
    if (talla_id     != null) params.append('talla_id',     talla_id);
    if (empresa_id   != null) params.append('empresa_id',   empresa_id);
    if (seccion_id   != null) params.append('seccion_id',   seccion_id);
    if (temporada_id != null) params.append('temporada_id', temporada_id);
    const query = params.toString();
    return apiClient.get(`/stats/inventario${query ? `?${query}` : ''}`);
};
