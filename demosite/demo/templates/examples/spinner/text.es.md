---
title: Indicador de Carga
---

# Indicador de carga / spinner

Un patrón común es mostrar un indicador de carga (también llamado "spinner"), cada vez que la duración de una solicitud es más larga de lo que el usuario habitual está dispuesto a esperar, sin ponerse nervioso...

{% md_include_source "demo/components/examples/spinner/__init__.py" %}
{% md_include_source "demo/components/examples/spinner/spinner.html" %}

Necesitarás un poco de CSS para que esto funcione, ya que tienes que ocultar el spinner por defecto:

{% md_include_source "demo/components/examples/spinner/spinner.css" %}

También puedes lograr la ocultación con `opacity: 0` y `opacity:1` con una `transition` para hacerlo más suave.

Puedes hacer clic en el botón de abajo, el spinner se muestra durante el período de la solicitud de tetra y se oculta de nuevo después.