---
title: Clic para Editar
---

# Clic para Editar

El patrón *clic para editar* permite la edición en línea de un registro sin refrescar la página.

Esta es una forma sencilla de implementar esto como un componente de Tetra, incluyendo botones de guardar/cancelar:
{% md_include_source "demo/components/examples/click_to_edit/__init__.py" %}
{% md_include_source "demo/components/examples/click_to_edit/click_to_edit.html" %}

Si haces clic en el texto, se reemplaza con un campo de formulario de entrada.

También podrías imaginar hacerlo de otras maneras:

* ocultando los bordes del campo de entrada en el modo de visualización y mostrándolos de nuevo usando Alpine cuando se está en `edit_mode`.
* sin botones, simplemente usando el evento `@blur` para guardar.