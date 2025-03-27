const Tetra = {
  init() {
    Alpine.magic('static', () => Tetra.$static);
  },

  $static() {
    return (path) => {
      return window.__tetra_staticRoot+path;
    }
  },

  alpineComponentMixins() {
    return {
      // Alpine.js lifecycle:
      init() {
        this.$dispatch('tetra:child-component-init', {component:  this});
        this.__initServerWatchers();
        if (this.__initInner) {
          this.__initInner();
        }
      },
      destroy() {
        this.$dispatch('tetra:child-component-destroy', {component:  this});
        if (this.__destroyInner) {
          this.__destroyInner();
        }
      },

      // Tetra built ins:
      _updateHtml(html) {
        Alpine.morph(this.$root, html, {
          updating(el, toEl, childrenOnly, skip) {
            if (toEl.hasAttribute && toEl.hasAttribute('x-data-maintain') && el.hasAttribute && el.hasAttribute('x-data')) {
              toEl.setAttribute('x-data', el.getAttribute('x-data'));
              toEl.removeAttribute('x-data-maintain');
            } else if (toEl.hasAttribute && toEl.hasAttribute('x-data-update') && el.hasAttribute && el.hasAttribute('x-data')) {
              let data = Tetra.jsonDecode(toEl.getAttribute('x-data-update'));
              let old_data = Tetra.jsonDecode(toEl.getAttribute('x-data-update-old'));
              let comp = window.Alpine.$data(el);
              for (const key in data) {
                if (old_data.hasOwnProperty(key) && (old_data[key] !== comp[key])) {
                  // If the data that was submitted to the server has since changed we don't overwrite it
                  continue
                }
                comp[key] = data[key];
              }
              toEl.setAttribute('x-data', el.getAttribute('x-data'));
              toEl.removeAttribute('x-data-update');
            }
          },
          lookahead: true
        });
        this.$dispatch('tetra:component-updated', { component: this });
      },
      _updateData(data) {
        for (const key in data) {
          this[key] = data[key];
        }
        this.$dispatch('tetra:component-data-updated', { component: this });
      },
      _setValueByName(name, value){
        // sets value to the input field with the given name
        // This is especially useful for emptying a file field, as the browser doesn't do that on page refreshes.
        let inputs = document.getElementsByName(name);
        for (let i = 0; i < inputs.length; i++) {
          inputs[i].value = value;
        }
      },
      _removeComponent() {
        this.$dispatch('tetra:component-before-remove', { component: this });
        this.$root.remove();
      },
      _replaceComponent(html) {
        this.$dispatch('tetra:component-before-remove', { component: this });
        this.$root.insertAdjacentHTML('afterend', html);
        this.$root.remove();
        this.$dispatch('tetra:component-updated', { component: this });
      },
      _redirect(url) {
        document.location = url;
      },
      _dispatch(name, data) {
        this.$dispatch(name, {
          _component: this,
          ...data
        });
      },
      _pushUrl(url, replace=false) {
        if(replace){
          window.history.replaceState(null, '', url);
        } else {
          window.history.pushState(null, '', url);
        }
      },
      _uploadFile(event) {
        // TODO: Consider how multiple files can be handled
        const file = event.target.files[0];
        const method = '_upload_temp_file';
        const endpoint = this.__serverMethods.find(item => item.name === '_upload_temp_file').endpoint;
        const args = [event.target.name, event.target.files[0].name];
        Tetra.callServerMethodWithFile(this, method, endpoint, file, args).then((result) => {
          //TODO: Determine if we need to do anything with the resulting filename
          //event.target.dataset.tetraTempFileName = result;
          //this._updateData(result);
        });

      },
      // Tetra private:
      __initServerWatchers() {
        this.__serverMethods.forEach(item => {
          if (item.watch) {
            item.watch.forEach(propName => {
              this.$watch(propName, async (value, oldValue) => {
                await this[item.name](value, oldValue, propName);
              })
            })
          }
        })
      },
      __childComponents: {},
      __rootBind: {
        ['@tetra:child-component-init'](event) {
          event.stopPropagation();
          const comp = event.detail.component;
          if (comp.key === this.key) {
            return
          }
          if (comp.key) {
            this.__childComponents[comp.key] = comp;
          }
          comp._parent = this;
        },
        ['@tetra:child-component-destroy'](event) {
          event.stopPropagation();
          const comp = event.detail.component;
          if (comp.key === this.key) {
            return
          }
          delete this.__childComponents[comp.key];
          event.detail.component._parent = null;
        }
      }
    }
  },

  makeServerMethods(serverMethods) {
    const methods = {};
    serverMethods.forEach((serverMethod) => {
      var func = async function(...args) {
        // TODO: ensure only one concurrent?
        return await Tetra.callServerMethod(this, serverMethod.name, serverMethod.endpoint, args)
      }
      if (serverMethod.debounce) {
        func = Tetra.debounce(func, serverMethod.debounce, serverMethod.debounce_immediate)
      } else if (serverMethod.throttle) {
        func = Tetra.throttle(func, serverMethod.throttle, {
          leading: serverMethod.throttle_leading,
          trailing: serverMethod.throttle_trailing
        })
      }
      methods[serverMethod.name] = func;
    })
    return methods
  },

  makeAlpineComponent(componentName, script, serverMethods, serverProperties) {
    Alpine.data(
        componentName,
        (initialDataJson) => {
          const {init, destroy, ...script_rest} = script;
          const initialData = Tetra.jsonDecode(initialDataJson);
          const data = {
            componentName,
            __initInner: init,
            __destroyInner: destroy,
            __serverMethods: serverMethods,
            __serverProperties: serverProperties,
            ...(initialData || {}),
            ...script_rest,
            ...Tetra.makeServerMethods(serverMethods),
            ...Tetra.alpineComponentMixins(),
          }
          return data
        }
    )
  },

  getStateWithChildren(component) {
    const data = {}
    component.__serverProperties.forEach((key) => {
      data[key] = component[key]
    })
    const r = {
      state: component.__state,
      data: data,
      children: []
    }
    for (const key in component.__childComponents) {
      const comp = component.__childComponents[key];
      r.children.push(Tetra.getStateWithChildren(comp));
    }
    return r;
  },

  loadScript(src) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.onload = resolve;
      script.onerror = reject;
      document.head.appendChild(script);
    });
  },

  loadStyles(href) {
    return new Promise((resolve, reject) => {
      const link = document.createElement('link');
      link.href = href;
      link.rel  = 'stylesheet';
      link.type = 'text/css';
      link.onload = resolve;
      link.onerror = reject;
      document.head.appendChild(link);
    });
  },

  async handleServerMethodResponse(response, component) {
    if (response.status === 200) {
      if (response.headers.get('T-Response') !== "true") {
        console.error("Response is not a Tetra response. Please check the server implementation.");
        return
      }
      // handle Django messages and emit "tetra:newmessage" for each one, so components can react on that individually
      const messages = Tetra.jsonDecode(response.headers.get('T-Messages'));
      if (messages) {
        messages.forEach((message, index) => {
            component.$dispatch('tetra:newmessage', message)
        })
      }
      const respData = Tetra.jsonDecode(await response.text());
      if (respData.success) {
        let loadingResources = [];
        respData.js.forEach(src => {
          if (!document.querySelector(`script[src="${CSS.escape(src)}"]`)) {
            loadingResources.push(Tetra.loadScript(src));
          }
        })
        respData.styles.forEach(src => {
          if (!document.querySelector(`link[href="${CSS.escape(src)}"]`)) {
            loadingResources.push(Tetra.loadStyles(src));
          }
        })
        await Promise.all(loadingResources);
        if (respData.callbacks) {
          respData.callbacks.forEach((item) => {
            // iterate down path to callback
            let obj = component;
            item.callback.forEach((name, i) => {
              if (i === item.callback.length-1) {
                obj[name](...item.args);
              } else {
                obj = obj[name];
                console.log(name, obj)
              }
            })
          })
        }
        return respData.result;
      } else {
        // TODO: better errors
        throw new Error('Error processing public method');
      }
    } else {
      throw new Error(`Server responded with an error ${response.status} (${response.statusText})`);
    }
  },
  async callServerMethod(component, methodName, methodEndpoint, args) {
    // TODO: error handling
    let body = Tetra.getStateWithChildren(component);
    body.args = args;
    const response = await fetch(methodEndpoint, {
      method: 'POST',
      headers: {
        'T-Request': "true",
        'T-Current-URL': document.location.href,
        'Content-Type': 'application/json',
        'X-CSRFToken': window.__tetra_csrfToken,
      },
      mode: 'same-origin',
      body: Tetra.jsonEncode(body),
    });
    return await this.handleServerMethodResponse(response, component);
  },

  async callServerMethodWithFile(component, methodName, methodEndpoint, file, args) {
    // TODO: error handling and add security to prevent arbitrary file uploads
    let state = Tetra.getStateWithChildren(component);
    state.args = args;
    let formData = new FormData();
    formData.append('file', file);
    formData.append('state', Tetra.jsonEncode(state));
    //body.args = args;
    const response = await fetch(methodEndpoint, {
      method: 'POST',
      headers: {
        'T-Request': "true",
        'T-Current-URL': document.location.href,
        //'Content-Type': 'application/json',
        'X-CSRFToken': window.__tetra_csrfToken,
      },
      mode: 'same-origin',
      body: formData,
    });
    return await this.handleServerMethodResponse(response, component);
  },

  jsonReplacer(key, value) {
    if (value instanceof Date) {
      return {
        __type: 'datetime',
        value: value.toISOString(),
      };
    } else if (value instanceof Set) {
      return {
        __type: 'set',
        value: Array.from(value)
      };
    }
    return value;
  },

  jsonReviver(key, value) {
    if (value && typeof value === 'object' && value.__type) {
      if (value.__type === 'datetime') {
        return new Date(value);
      } else if (value.__type === 'set') {
        return new Set(value);
      }
    }
    return value
  },

  jsonEncode(obj) {
    return JSON.stringify(obj, Tetra.jsonReplacer);
  },

  jsonDecode(s) {
    return JSON.parse(s, Tetra.jsonReviver)
  },

  debounce(func, wait, immediate) {
    var timeout
    return function() {
      var context = this, args = arguments
      var later = function () {
        timeout = null
        if (!immediate) func.apply(context, args);
      }
      var callNow = immediate && !timeout;
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
      if (callNow) func.apply(context, args);
    }
  },

  throttle(func, wait, options) {
    // From Underscore.js
    // https://underscorejs.org
    // (c) 2009-2022 Jeremy Ashkenas, Julian Gonggrijp, and DocumentCloud and
    // Investigative Reporters & Editors
    // Underscore may be freely distributed under the MIT license.
    // --
    // Returns a function, that, when invoked, will only be triggered at most once
    // during a given window of time. Normally, the throttled function will run
    // as much as it can, without ever going more than once per `wait` duration;
    // but if you'd like to disable the execution on the leading edge, pass
    // `{leading: false}`. To disable execution on the trailing edge, ditto.
    var timeout, context, args, result;
    var previous = 0;
    if (!options) options = {};

    var later = function() {
      previous = options.leading === false ? 0 : now();
      timeout = null;
      result = func.apply(context, args);
      if (!timeout) context = args = null;
    };

    var throttled = function() {
      var _now = new Date().getTime();
      if (!previous && options.leading === false) previous = _now;
      var remaining = wait - (_now - previous);
      context = this;
      args = arguments;
      if (remaining <= 0 || remaining > wait) {
        if (timeout) {
          clearTimeout(timeout);
          timeout = null;
        }
        previous = _now;
        result = func.apply(context, args);
        if (!timeout) context = args = null;
      } else if (!timeout && options.trailing !== false) {
        timeout = setTimeout(later, remaining);
      }
      return result;
    };

    throttled.cancel = function() {
      clearTimeout(timeout);
      previous = 0;
      timeout = context = args = null;
    };

    return throttled;
  }

}

export default Tetra;
