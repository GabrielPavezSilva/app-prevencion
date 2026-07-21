import { useEffect, useState } from 'react';
import { useTheme } from '../context/ThemeContext';

// Recharts necesita colores concretos (no acepta var() en sus props SVG).
// Este hook lee las variables CSS del tema actual y se recalcula al cambiar de tema.
// ponytail: lectura directa de getComputedStyle; sin libs de theming.
const read = (name, fallback) => {
  if (typeof window === 'undefined') return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
};

/**
 * @param {Record<string,[string,string]>} spec  clave -> [nombreVarCSS, fallback]
 * @returns {Record<string,string>}
 */
export function useThemeColors(spec) {
  const { theme } = useTheme();
  const [colors, setColors] = useState(() => {
    const out = {};
    for (const k in spec) out[k] = spec[k][1];
    return out;
  });

  useEffect(() => {
    const out = {};
    for (const k in spec) out[k] = read(spec[k][0], spec[k][1]);
    setColors(out);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  return colors;
}
