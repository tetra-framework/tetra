---
title: Indicador de Carga
---

# Indicador de carga / spinner

Un patrón común es mostrar un indicador de carga (también llamado "spinner"), cada vez que la duración de una solicitud es más larga de lo que el usuario habitual está dispuesto a esperar, sin ponerse nervioso...

Existen varios spinners disponibles en frameworks como [Bootstrap](https://getbootstrap.com/docs/5/components/spinners/) o [tabler.io](https://docs.tabler.io/ui/components/spinners) (que se basa en BS5). Incluso Tailwind utiliza una [clase de animación](https://tailwindcss.com/docs/animation#adding-a-spin-animation) para producir spinners.

Tetra intenta ser lo más agnóstico posible respecto a frameworks; aquí usaremos Bootstrap 5 en el ejemplo:

{% md_include_source "demo/components/examples/spinner/__init__.py" %}
{% md_include_source "demo/components/examples/spinner/spinner.html" %}

El spinner está oculto por defecto y se muestra cuando hay una solicitud de Tetra en curso.

También puedes lograr la ocultación usando `opacity: 0` y `opacity: 1` junto con una `transition` para que el efecto sea más suave; consulta la [documentación del spinner](https://tetra.readthedocs.io/en/stable/helpers/#loading-indicators-spinners) para más detalles.

Puedes hacer clic en los botónes de abajo: los spinners se muestras durante el período de la solicitud de Tetra y se ocultan de nuevo después, independientemente de dónde esté ubicado el spinner en la pagina.
