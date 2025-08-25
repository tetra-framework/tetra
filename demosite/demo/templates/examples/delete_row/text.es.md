---
title: Eliminar Fila
---

# Eliminar Fila

Aquí hay un componente de ejemplo que demuestra cómo crear un botón de eliminar que quita una fila de la tabla al hacer clic.

{% md_include_source "demo/components/examples/delete_row_table/__init__.py" %}
{% md_include_source "demo/components/examples/delete_row_table/delete_row_table.html" %}

Hasta aquí el componente de la tabla. Las filas son componentes en sí mismas. Cada fila es responsable de su propia eliminación. Por lo tanto, no es necesario un `delete_item(algun_id)`, ya que el componente ya conoce su id porque guarda su estado internamente. `delete_item()` es suficiente dentro del código de la plantilla del componente.

{% md_include_source "demo/components/examples/delete_row/__init__.py" %}

{% md_include_source "demo/components/examples/delete_row/delete_row.html" %}