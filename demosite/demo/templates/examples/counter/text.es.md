---
title: Contador
---

# Demostración del Contador

El "contador" es básicamente la demostración "Hola Mundo" de los componentes. Es una demostración simple de cómo usar los componentes de Tetra.

El componente en sí solo proporciona un atributo `count` y un método público `increment()`.

Suficiente charla, muéstrame el código.

{% md_include_component_source "examples.Counter" %}

El renderizado es sencillo.

{% md_include_component_template "examples.Counter" %}

Observa en la demostración a continuación qué tan rápido es el renderizado de Tetra. Las actualizaciones de los componentes se sienten casi tan rápidas como el Javascript nativo.