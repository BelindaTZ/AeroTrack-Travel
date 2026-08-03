/* Selector de lugar — autocompletado local sobre datos ya cargados por el
   backend (sin fetch en vivo, sin dependencias). Ver
   app/shared/templates/_selector_lugar.html para el markup que este
   script mejora progresivamente: si este archivo no carga, el input
   sigue siendo un campo de texto normal con su `name` real, el form
   sigue funcionando exactamente igual que sin JS. */
(function () {
  'use strict';

  function escaparHtml(texto) {
    var div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
  }

  function resaltarCoincidencia(texto, consulta) {
    if (!consulta) return escaparHtml(texto);
    var idx = texto.toLowerCase().indexOf(consulta.toLowerCase());
    if (idx === -1) return escaparHtml(texto);
    var antes = texto.slice(0, idx);
    var medio = texto.slice(idx, idx + consulta.length);
    var despues = texto.slice(idx + consulta.length);
    return escaparHtml(antes) + '<strong>' + escaparHtml(medio) + '</strong>' + escaparHtml(despues);
  }

  function inicializar(wrapper) {
    var input = wrapper.querySelector('.selector-lugar-input');
    var panel = wrapper.querySelector('.selector-lugar-panel');
    if (!input || !panel) return;

    var opciones = [];
    try {
      opciones = JSON.parse(wrapper.getAttribute('data-opciones') || '[]');
    } catch (e) {
      opciones = [];
    }

    // Patrón de dos inputs: el visible pierde su `name` real y un hidden
    // lo hereda — así lo que se envía es siempre `valor` de la opción
    // elegida (o el texto crudo si el usuario no eligió nada de la lista).
    var nombreReal = input.name;
    input.removeAttribute('name');
    var oculto = document.createElement('input');
    oculto.type = 'hidden';
    oculto.name = nombreReal;
    oculto.value = input.value;
    wrapper.appendChild(oculto);

    // El panel se reubica como hijo directo de <body>: así escapa cualquier
    // ancestro con overflow:hidden o backdrop-filter (p. ej. el hero de home,
    // ver aerotrack.css) sin importar dónde viva este selector en la página.
    document.body.appendChild(panel);

    function posicionar() {
      var rect = input.getBoundingClientRect();
      panel.style.top = (rect.bottom + 6) + 'px';
      panel.style.left = rect.left + 'px';
      panel.style.width = rect.width + 'px';
    }

    function alScrollOResize() {
      if (!panel.hidden) posicionar();
    }
    window.addEventListener('scroll', alScrollOResize, true);
    window.addEventListener('resize', alScrollOResize);

    var resaltadoIdx = -1;
    var visibles = [];

    function cerrar() {
      panel.hidden = true;
      panel.innerHTML = '';
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      resaltadoIdx = -1;
      visibles = [];
    }

    function seleccionar(opcion) {
      input.value = opcion.principal;
      oculto.value = opcion.valor;
      cerrar();
    }

    function marcarResaltado() {
      var items = panel.querySelectorAll('.selector-lugar-item');
      items.forEach(function (item, i) {
        var activo = i === resaltadoIdx;
        item.classList.toggle('resaltado', activo);
        if (activo) {
          input.setAttribute('aria-activedescendant', item.id);
          item.scrollIntoView({ block: 'nearest' });
        }
      });
    }

    function renderizar(consulta) {
      var q = (consulta || '').trim().toLowerCase();

      if (!q) {
        cerrar();
        return;
      }

      visibles = opciones.filter(function (o) {
        return (o.principal && o.principal.toLowerCase().indexOf(q) !== -1) ||
               (o.secundario && o.secundario.toLowerCase().indexOf(q) !== -1);
      }).slice(0, 8);

      panel.innerHTML = '';
      resaltadoIdx = -1;

      if (visibles.length === 0) {
        var vacio = document.createElement('li');
        vacio.className = 'selector-lugar-vacio';
        vacio.textContent = 'No encontramos coincidencias';
        panel.appendChild(vacio);
      } else {
        visibles.forEach(function (opcion, i) {
          var item = document.createElement('li');
          item.className = 'selector-lugar-item';
          item.id = (wrapper.id || 'selector') + '-opt-' + i;
          item.setAttribute('role', 'option');
          var secundarioHtml = opcion.secundario
            ? '<span class="selector-lugar-item-sub">' + escaparHtml(opcion.secundario) + '</span>'
            : '';
          item.innerHTML =
            '<i class="bi bi-geo-alt selector-lugar-item-icon" aria-hidden="true"></i>' +
            '<span class="selector-lugar-item-texto">' +
            '<span class="selector-lugar-item-principal">' + resaltarCoincidencia(opcion.principal, q) + '</span>' +
            secundarioHtml +
            '</span>';
          item.addEventListener('mousedown', function (ev) {
            ev.preventDefault(); // evita que el blur cierre el panel antes del click
            seleccionar(opcion);
          });
          panel.appendChild(item);
        });
      }

      posicionar();
      panel.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }

    input.addEventListener('input', function () {
      oculto.value = input.value; // conserva el texto crudo si no se elige ninguna sugerencia
      renderizar(input.value);
    });

    input.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowDown') {
        ev.preventDefault();
        if (panel.hidden) { renderizar(input.value); return; }
        if (visibles.length) {
          resaltadoIdx = (resaltadoIdx + 1) % visibles.length;
          marcarResaltado();
        }
      } else if (ev.key === 'ArrowUp') {
        ev.preventDefault();
        if (visibles.length) {
          resaltadoIdx = (resaltadoIdx - 1 + visibles.length) % visibles.length;
          marcarResaltado();
        }
      } else if (ev.key === 'Enter') {
        if (resaltadoIdx >= 0 && visibles[resaltadoIdx]) {
          ev.preventDefault();
          seleccionar(visibles[resaltadoIdx]);
        }
      } else if (ev.key === 'Escape') {
        cerrar();
      }
    });

    input.addEventListener('blur', function () {
      // Delay corto: si el blur vino de clickear una opción, el mousedown
      // de arriba ya hizo preventDefault + seleccionó antes de que esto corra.
      setTimeout(cerrar, 100);
    });

    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');
    panel.setAttribute('role', 'listbox');
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-selector-lugar]').forEach(inicializar);
  });
})();
