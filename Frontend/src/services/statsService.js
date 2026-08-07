import { apiClient } from './api';

/**
 * Métricas del dashboard EPP.
 *
 * `desde`/`hasta` son fechas locales (YYYY-MM-DD) y acotan los KPI, el donut de
 * motivos y los rankings. `meses` controla solo la ventana de la serie mensual,
 * que termina en el mes de `hasta`.
 */
export const getDashboard = ({ desde, hasta, empresa_id, area_id, meses } = {}) => {
    const params = new URLSearchParams();
    if (desde) params.append('desde', desde);
    if (hasta) params.append('hasta', hasta);
    if (empresa_id != null) params.append('empresa_id', empresa_id);
    if (area_id != null) params.append('area_id', area_id);
    if (meses != null) params.append('meses', meses);
    const query = params.toString();
    return apiClient.get(`/stats/dashboard${query ? `?${query}` : ''}`);
};
