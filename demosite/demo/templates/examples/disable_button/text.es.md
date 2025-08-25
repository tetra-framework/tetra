---
title: Deshabilitar botón de envío
---

# Deshabilitar botón de envío

Al enviar un formulario, muchos usuarios tienden a hacer doble clic en el botón de `enviar`, lo que puede provocar entradas duplicadas en las bases de datos si el momento es el adecuado ;-)

Un patrón sencillo es simplemente deshabilitar el botón justo después de hacer clic. Puedes hacer dos cosas en el listener `@click`: deshabilitar el botón *y* llamar a `submit()`.

{% md_include_source "demo/components/examples/disable_button/disable_button.html" %}


Si haces clic en el botón, este se deshabilita sin alterar el estado. Cuando el componente se vuelve a cargar, el botón se habilita de nuevo (en el caso de un formulario de creación), pero la mayoría de las veces, redirigirás a otra página usando `self.client._redirect(...)`