(() => {
  let __script = {{ component_script|safe }};
  let __serverMethods = {{ component_server_methods|safe }};
  let __serverProperties = {{ component_server_properties|safe }};
  let __componentName = '{{ component_name|safe }}';
  window.document.addEventListener('alpine:init', () => {
    Tetra.makeAlpineComponent(
      __componentName,
      __script,
      __serverMethods,
      __serverProperties,
    )
  })
})();