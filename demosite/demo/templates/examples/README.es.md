# Ejemplos

Este directorio contiene ejemplos de Tetra. Sigue una estructura determinada:

```
nombre_del_ejemplo/
  demo.html
  text.md
  componente.py
otro_ejemplo/
  demo.html
  text.md
  componente.py
```

* El archivo `text.md` contiene la descripción del ejemplo, con secciones de código. Esto se renderiza como HTML. Debe contener un `title` en el front matter. Puedes incluir archivos de código fuente usando `{% md_include_source 'ruta/al/archivo' 'comentario_opcional_primera_linea' %}`
* La parte `demo.html`, que es una plantilla de Django que usa el componente Tetra, se renderiza.