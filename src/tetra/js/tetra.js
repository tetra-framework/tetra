import Tetra from './tetra.core'

window.Tetra = Tetra;
window.document.addEventListener('alpine:init', () => {
  Tetra.init();
})
