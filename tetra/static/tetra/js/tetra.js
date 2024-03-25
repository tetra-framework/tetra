(() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropSymbols = Object.getOwnPropertySymbols;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __propIsEnum = Object.prototype.propertyIsEnumerable;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __spreadValues = (a, b) => {
    for (var prop in b || (b = {}))
      if (__hasOwnProp.call(b, prop))
        __defNormalProp(a, prop, b[prop]);
    if (__getOwnPropSymbols)
      for (var prop of __getOwnPropSymbols(b)) {
        if (__propIsEnum.call(b, prop))
          __defNormalProp(a, prop, b[prop]);
      }
    return a;
  };
  var __objRest = (source, exclude) => {
    var target = {};
    for (var prop in source)
      if (__hasOwnProp.call(source, prop) && exclude.indexOf(prop) < 0)
        target[prop] = source[prop];
    if (source != null && __getOwnPropSymbols)
      for (var prop of __getOwnPropSymbols(source)) {
        if (exclude.indexOf(prop) < 0 && __propIsEnum.call(source, prop))
          target[prop] = source[prop];
      }
    return target;
  };

  // js/tetra.core.js
  var Tetra = {
    init() {
      Alpine.magic("static", () => Tetra.$static);
    },
    $static() {
      return (path) => {
        return window.__tetra_staticRoot + path;
      };
    },
    alpineComponentMixins() {
      return {
        init() {
          this.$dispatch("tetra:child-component-init", { component: this });
          this.__initServerWatchers();
          if (this.__initInner) {
            this.__initInner();
          }
        },
        destroy() {
          this.$dispatch("tetra:child-component-destroy", { component: this });
          if (this.__destroyInner) {
            this.__destroyInner();
          }
        },
        _updateHtml(html) {
          Alpine.morph(this.$root, html, {
            updating(el, toEl, childrenOnly, skip) {
              if (toEl.hasAttribute && toEl.hasAttribute("x-data-maintain") && el.hasAttribute && el.hasAttribute("x-data")) {
                toEl.setAttribute("x-data", el.getAttribute("x-data"));
                toEl.removeAttribute("x-data-maintain");
              } else if (toEl.hasAttribute && toEl.hasAttribute("x-data-update") && el.hasAttribute && el.hasAttribute("x-data")) {
                let data = Tetra.jsonDecode(toEl.getAttribute("x-data-update"));
                let old_data = Tetra.jsonDecode(toEl.getAttribute("x-data-update-old"));
                let comp = window.Alpine.$data(el);
                for (const key in data) {
                  if (old_data.hasOwnProperty(key) && old_data[key] !== comp[key]) {
                    continue;
                  }
                  comp[key] = data[key];
                }
                toEl.setAttribute("x-data", el.getAttribute("x-data"));
                toEl.removeAttribute("x-data-update");
              }
            },
            lookahead: true
          });
        },
        _updateData(data) {
          for (const key in data) {
            this[key] = data[key];
          }
        },
        _removeComponent() {
          this.$root.remove();
        },
        _replaceComponentAndState(html) {
          this.$root.insertAdjacentHTML("afterend", html);
          this.$root.remove();
        },
        _redirect(url) {
          document.location = url;
        },
        _dispatch(name, data) {
          this.$dispatch(name, __spreadValues({
            _component: this
          }, data));
        },
        __initServerWatchers() {
          this.__serverMethods.forEach((item) => {
            if (item.watch) {
              item.watch.forEach((propName) => {
                this.$watch(propName, async (value, oldValue) => {
                  await this[item.name](value, oldValue, propName);
                });
              });
            }
          });
        },
        __childComponents: {},
        __rootBind: {
          ["@tetra:child-component-init"](event) {
            event.stopPropagation();
            const comp = event.detail.component;
            if (comp.key === this.key) {
              return;
            }
            if (comp.key) {
              this.__childComponents[comp.key] = comp;
            }
            comp._parent = this;
          },
          ["@tetra:child-component-destroy"](event) {
            event.stopPropagation();
            const comp = event.detail.component;
            if (comp.key === this.key) {
              return;
            }
            delete this.__childComponents[comp.key];
            event.detail.component._parent = null;
          }
        }
      };
    },
    makeServerMethods(serverMethods) {
      const methods = {};
      serverMethods.forEach((serverMethod) => {
        var func = async function(...args) {
          return await Tetra.callServerMethod(this, serverMethod.name, serverMethod.endpoint, args);
        };
        if (serverMethod.debounce) {
          func = Tetra.debounce(func, serverMethod.debounce, serverMethod.debounce_immediate);
        } else if (serverMethod.throttle) {
          func = Tetra.throttle(func, serverMethod.throttle, {
            leading: serverMethod.throttle_leading,
            trailing: serverMethod.throttle_trailing
          });
        }
        methods[serverMethod.name] = func;
      });
      return methods;
    },
    makeAlpineComponent(componentName, script, serverMethods, serverProperties) {
      Alpine.data(componentName, (initialDataJson) => {
        const _a = script, { init, destroy } = _a, script_rest = __objRest(_a, ["init", "destroy"]);
        const initialData = Tetra.jsonDecode(initialDataJson);
        const data = __spreadValues(__spreadValues(__spreadValues(__spreadValues({
          componentName,
          __initInner: init,
          __destroyInner: destroy,
          __serverMethods: serverMethods,
          __serverProperties: serverProperties
        }, initialData || {}), script_rest), Tetra.makeServerMethods(serverMethods)), Tetra.alpineComponentMixins());
        return data;
      });
    },
    getStateWithChildren(component) {
      const data = {};
      component.__serverProperties.forEach((key) => {
        data[key] = component[key];
      });
      const r = {
        state: component.__state,
        data,
        children: []
      };
      for (const key in component.__childComponents) {
        const comp = component.__childComponents[key];
        r.children.push(Tetra.getStateWithChildren(comp));
      }
      return r;
    },
    loadScript(src) {
      return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    },
    loadStyles(href) {
      return new Promise((resolve, reject) => {
        const link = document.createElement("link");
        link.href = href;
        link.rel = "stylesheet";
        link.type = "text/css";
        link.onload = resolve;
        link.onerror = reject;
        document.head.appendChild(link);
      });
    },
    async callServerMethod(component, methodName, methodEndpoint, args) {
      body = Tetra.getStateWithChildren(component);
      body.args = args;
      const response = await fetch(methodEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": window.__tetra_csrfToken
        },
        mode: "same-origin",
        body: Tetra.jsonEncode(body)
      });
      if (response.status === 200) {
        const respData = Tetra.jsonDecode(await response.text());
        if (respData.success) {
          let loadingResources = [];
          respData.js.forEach((src) => {
            if (!document.querySelector(`script[src="${CSS.escape(src)}"]`)) {
              loadingResources.push(Tetra.loadScript(src));
            }
          });
          respData.styles.forEach((src) => {
            if (!document.querySelector(`link[href="${CSS.escape(src)}"]`)) {
              loadingResources.push(Tetra.loadStyles(src));
            }
          });
          await Promise.all(loadingResources);
          if (respData.callbacks) {
            respData.callbacks.forEach((item) => {
              let obj = component;
              item.callback.forEach((name, i) => {
                if (i === item.callback.length - 1) {
                  obj[name](...item.args);
                } else {
                  obj = obj[name];
                  console.log(name, obj);
                }
              });
            });
          }
          return respData.result;
        } else {
          throw new Error("Error processing public method");
        }
      } else {
        throw new Error(`Server responded with an error ${response.status} (${response.statusText})`);
      }
    },
    jsonReplacer(key, value) {
      if (value instanceof Date) {
        return {
          __type: "datetime",
          value: value.toISOString()
        };
      } else if (value instanceof Set) {
        return {
          __type: "set",
          value: Array.from(value)
        };
      }
      return value;
    },
    jsonReviver(key, value) {
      if (value && typeof value === "object" && value.__type) {
        if (value.__type === "datetime") {
          return new Date(value);
        } else if (value.__type === "set") {
          return new Set(value);
        }
      }
      return value;
    },
    jsonEncode(obj) {
      return JSON.stringify(obj, Tetra.jsonReplacer);
    },
    jsonDecode(s) {
      var obj = JSON.parse(s, Tetra.jsonReviver);
      return obj;
    },
    debounce(func, wait, immediate) {
      var timeout;
      return function() {
        var context = this, args = arguments;
        var later = function() {
          timeout = null;
          if (!immediate)
            func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow)
          func.apply(context, args);
      };
    },
    throttle(func, wait, options) {
      var timeout, context, args, result;
      var previous = 0;
      if (!options)
        options = {};
      var later = function() {
        previous = options.leading === false ? 0 : now();
        timeout = null;
        result = func.apply(context, args);
        if (!timeout)
          context = args = null;
      };
      var throttled = function() {
        var _now = new Date().getTime();
        if (!previous && options.leading === false)
          previous = _now;
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
          if (!timeout)
            context = args = null;
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
  };
  var tetra_core_default = Tetra;

  // js/tetra.js
  window.Tetra = tetra_core_default;
  window.document.addEventListener("alpine:init", () => {
    tetra_core_default.init();
  });
})();
//# sourceMappingURL=tetra.js.map
