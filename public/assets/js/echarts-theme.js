/**
 * AeroTrack Travel — configuración base de ECharts para los dashboards.
 * Colores tomados de public/assets/css/aerotrack.css (Design System v4,
 * Sky Blue × Modernist). ECharts dibuja en <canvas>, así que no puede leer
 * var(--x) del DOM — los valores están hardcodeados acá, calcados 1:1 de
 * los tokens reales (no la paleta genérica azul/verde/naranja/morado).
 */
const AEROTRACK_COLORS = [
  '#0072ce', // --sky-800   (primario)
  '#dd2b0f', // --coral-600 (accent)
  '#198754', // --green-600 (éxito)
  '#4fa6e8', // --sky-400   (azul claro)
  '#ff9783', // --coral-400 (coral claro)
  '#7d7979', // --neutral-600 (gris, series "otros")
];

const AEROTRACK_SEMANTIC = {
  primary: '#0072ce',
  accent: '#dd2b0f',
  success: '#198754',
  danger: '#dc3545',
  muted: '#7d7979',
  border: '#d7d3d3',
  text: '#2d2b2b',
};

const ECHARTS_BASE = {
  color: AEROTRACK_COLORS,
  textStyle: { fontFamily: 'Inter, system-ui, sans-serif', color: AEROTRACK_SEMANTIC.text },
  grid: { containLabel: true, left: '3%', right: '4%', top: 40, bottom: 30 },
  tooltip: { trigger: 'axis', confine: true },
  legend: { type: 'scroll', bottom: 0, textStyle: { color: AEROTRACK_SEMANTIC.muted, fontSize: 11 } },
};

/** Inicializa un chart en #elementId fusionando `option` sobre ECHARTS_BASE.
 * Devuelve null si el elemento no existe (evita errores en dashboards
 * donde un gráfico se oculta condicionalmente, ej. DB-04 sin cobertura BTS/FAA). */
function initChart(elementId, option) {
  const el = document.getElementById(elementId);
  if (!el || typeof echarts === 'undefined') return null;
  const chart = echarts.init(el, null, { renderer: 'canvas' });
  chart.setOption({ ...ECHARTS_BASE, ...option });
  window.addEventListener('resize', () => chart.resize());
  return chart;
}
