/* Fix global 3 (auditoría de WorkPanels, 2026-07-31) — REG-J9 de la
   constitución: ningún filtro lleva botón "Aplicar"/"Buscar", se aplica
   solo al cambiar su valor. Selects/fechas/checkboxes/radios se envían al
   instante (evento change); los campos de texto esperan a que el usuario
   deje de tipear (debounce) para no navegar en cada tecla.

   Uso: marcar el <form> de filtros con data-auto-filtros — se conecta
   solo al cargar la página, sin llamar nada desde el template:

     <form method="get" data-auto-filtros>...</form>
*/
(function () {
    var DEMORA_MS = 450;

    function conectar(form) {
        var timer = null;

        form.querySelectorAll('select, input[type="date"], input[type="checkbox"], input[type="radio"]')
            .forEach(function (el) {
                el.addEventListener('change', function () { form.requestSubmit(); });
            });

        form.querySelectorAll('input[type="text"], input[type="search"], input[type="email"], input[type="number"]')
            .forEach(function (el) {
                el.addEventListener('input', function () {
                    clearTimeout(timer);
                    timer = setTimeout(function () { form.requestSubmit(); }, DEMORA_MS);
                });
            });
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('form[data-auto-filtros]').forEach(conectar);
    });
})();
