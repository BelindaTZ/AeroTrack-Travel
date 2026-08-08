/**
 * Selector de período reutilizable para los dashboards del backoffice
 * (DB-01 a DB-13 salvo DB-04, que no tiene filtro de período). 5 opciones
 * fijas por spec: Hoy / Esta semana / Este mes / Últimos 3 meses / Rango
 * personalizado — sin recarga de página, dispara `onChange({desde, hasta})`
 * en formato YYYY-MM-DD.
 *
 * Uso en el template:
 *   <div id="selector-periodo" class="filter-bar mb-3"></div>
 *   <script>
 *     initSelectorPeriodo('selector-periodo', function (periodo) {
 *       cargarDatosDashboard(periodo.desde, periodo.hasta);
 *     });
 *   </script>
 */
function _isoLocal(date) {
    return date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0') + '-' + String(date.getDate()).padStart(2, '0');
}

function _rangoPreset(clave) {
    var hoy = new Date();
    var desde = new Date(hoy);
    if (clave === 'hoy') {
        // desde == hasta == hoy
    } else if (clave === 'semana') {
        desde.setDate(hoy.getDate() - 7);
    } else if (clave === 'mes') {
        desde.setMonth(hoy.getMonth() - 1);
    } else if (clave === '3meses') {
        desde.setMonth(hoy.getMonth() - 3);
    } else if (clave === '6meses') {
        desde.setMonth(hoy.getMonth() - 6);
    } else if (clave === 'anio') {
        desde = new Date(hoy.getFullYear(), 0, 1);
    }
    return { desde: _isoLocal(desde), hasta: _isoLocal(hoy) };
}

var PRESETS_TACTICO = [
    { clave: 'hoy', label: 'Hoy' },
    { clave: 'semana', label: 'Esta semana' },
    { clave: 'mes', label: 'Este mes', activo: true },
    { clave: '3meses', label: 'Últimos 3 meses' },
    { clave: 'custom', label: 'Rango personalizado' },
];

// Dashboards estratégicos (DS-00 a DS-03) — granularidad mensual en
// ClickHouse, no tiene sentido "hoy"/"esta semana" ni rango personalizado
// libre (ver docs/estrategico-auditoria.md Fase C).
var PRESETS_ESTRATEGICO = [
    { clave: 'mes', label: 'Este mes', activo: true },
    { clave: '3meses', label: 'Últimos 3 meses' },
    { clave: '6meses', label: 'Últimos 6 meses' },
    { clave: 'anio', label: 'Año actual' },
];

function initSelectorPeriodo(elementId, onChange, presets) {
    var cont = document.getElementById(elementId);
    if (!cont) return;

    presets = presets || PRESETS_TACTICO;

    cont.innerHTML = presets.map(function (p) {
        return '<button type="button" class="btn-at-ghost' + (p.activo ? ' active' : '') + '" data-preset="' + p.clave + '">' + p.label + '</button>';
    }).join('') + '<input type="text" id="' + elementId + '-rango" class="form-control-at" style="max-width:220px;display:none" placeholder="Elegí un rango…">';

    var inputRango = document.getElementById(elementId + '-rango');
    var fp = null;
    if (typeof flatpickr !== 'undefined') {
        fp = flatpickr(inputRango, {
            mode: 'range',
            dateFormat: 'Y-m-d',
            onClose: function (selectedDates) {
                if (selectedDates.length === 2) {
                    onChange({ desde: _isoLocal(selectedDates[0]), hasta: _isoLocal(selectedDates[1]) });
                }
            },
        });
    }

    cont.querySelectorAll('[data-preset]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            cont.querySelectorAll('[data-preset]').forEach(function (b) { b.classList.remove('active'); });
            btn.classList.add('active');
            var clave = btn.dataset.preset;
            if (clave === 'custom') {
                inputRango.style.display = '';
                if (fp) fp.open();
                return;
            }
            inputRango.style.display = 'none';
            onChange(_rangoPreset(clave));
        });
    });

    // Carga inicial con el preset activo ("mes")
    onChange(_rangoPreset('mes'));
}
