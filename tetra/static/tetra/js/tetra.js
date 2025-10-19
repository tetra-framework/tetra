(() => {
  // tetra/js/tetra.core.js
  var Tetra = {
    ws: null,
    pendingSubscriptions: /* @__PURE__ */ new Map(),
    // Store subscriptions until WS is ready
    init() {
      Alpine.magic("static", () => Tetra.$static);
      if (window.__tetra_useWebsockets) {
        this.ensureWebSocketConnection();
      }
    },
    $static() {
      return (path) => {
        return window.__tetra_staticRoot + path;
      };
    },
    // Add WebSocket management methods
    ensureWebSocketConnection() {
      if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
        console.log("Connecting to Tetra WebSocket...");
        const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
        const ws_url = `${ws_scheme}://${window.location.host}/ws/tetra/`;
        this.ws = new WebSocket(ws_url);
        this.ws.onopen = () => {
          console.debug("Tetra WebSocket connected");
          this.pendingSubscriptions.forEach((data, componentId) => {
            this.ws.send(JSON.stringify(data));
          });
          this.pendingSubscriptions.clear();
        };
        this.ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
          this.handleWebsocketMessage(data);
        };
        this.ws.onclose = () => {
          console.log("Tetra WebSocket disconnected");
          setTimeout(() => {
            this.ensureWebSocketConnection();
          }, 3e3);
        };
        this.ws.onerror = (error) => {
          console.error("Tetra WebSocket error:", error);
        };
      }
      return this.ws;
    },
    _get_component_by_id(component_id) {
      const componentEl = document.querySelector(`[tetra-component-id="${component_id}"]`);
      if (!componentEl) {
        console.error(`AlpineJs Component with ID ${component_id} not found.`);
        return;
      }
      return Alpine.$data(componentEl);
    },
    _get_components_by_subscribe_group(group) {
      const componentEls = document.querySelectorAll("[tetra-subscription]");
      const matchingEls = Array.from(componentEls).filter((el) => {
        const subscribeAttr = el.getAttribute("tetra-subscription");
        const topics = subscribeAttr.split(",").map((t) => t.trim());
        return topics.includes(group);
      });
      return matchingEls.map((el) => Alpine.$data(el));
    },
    handleWebsocketMessage(data) {
      const dataType = data.type;
      switch (dataType) {
        case "subscription.response":
          this.handleSubscriptionResponse(data);
          break;
        case "notify":
          this.handleGroupNotify(data);
          break;
        case "component.update_data":
          this.handleComponentUpdateData(data);
          break;
        // case 'component.reload':
        //   this.handleComponentReload(data);
        //   break;
        case "component.remove":
          this.handleComponentRemove(data);
          break;
        default:
          console.warn("Unknown WebSocket message type:", dataType, ":", data);
      }
    },
    handleSubscriptionResponse(event) {
      switch (event["status"]) {
        case "subscribed":
          console.debug("Subscription to group", event["group"], "successful.");
          document.dispatchEvent(new CustomEvent(`tetra:component-subscribed`, {
            detail: {
              component: this,
              group: event["group"]
            }
          }));
          break;
        case "unsubscribed":
          console.debug("Subscription to group", event["group"], "redacted successfully.");
          document.dispatchEvent(new CustomEvent(`tetra:component-unsubscribed`, {
            detail: {
              component: this,
              group: event["group"]
            }
          }));
          break;
        case "error":
          console.error("Error subscribing component", event["component_id"], "to group", event["group"], ":", event["message"]);
          document.dispatchEvent(new CustomEvent(`tetra:component-subscription-error`, {
            detail: {
              component: this,
              group: event["group"],
              message: event["message"]
            }
          }));
          break;
        default:
          console.debug("Subscription response faulty:", event);
      }
    },
    handleGroupNotify(event) {
      const { group, event_name, data } = event;
      document.dispatchEvent(new CustomEvent(event_name, {
        detail: {
          data,
          group
        }
      }));
    },
    handleComponentUpdateData(event) {
      const { type, group, data } = event;
      const components = this._get_components_by_subscribe_group(group);
      components.forEach((component) => component._updateData(data));
    },
    handleComponentRemove(event) {
      const { type, group, component_id } = event;
      const component = this._get_component_by_id(component_id);
      if (component && component._removeComponent) {
        component._removeComponent();
      } else {
        component.remove();
        console.debug("Element with ID ${component_id} not identified as Alpine component, just removed it anyway.");
      }
    },
    sendWebSocketMessage(message) {
      if (!this.ws) {
        console.log("WebSocket is not connected. Cannot send message.");
        return;
      }
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(message));
      } else {
        if (message.type === "subscribe" && message.component_id) {
          this.pendingSubscriptions.set(message.component_id, message);
        }
        this.ws.addEventListener("open", () => {
          this.ws.send(JSON.stringify(message));
        }, { once: true });
      }
    },
    alpineComponentMixins() {
      return {
        // Alpine.js lifecycle:
        init() {
          this.component_id = this.$el.getAttribute("tetra-component-id");
          this.$dispatch("tetra:child-component-init", { component: this });
          this.__initServerWatchers();
          if (window.__tetra_useWebsockets && this.$el.hasAttribute("tetra-reactive")) {
            Tetra.ensureWebSocketConnection();
            const group = this.$el.getAttribute("tetra-subscription");
            if (group) {
              this._subscribe(group);
            }
          }
          if (this.__initInner) {
            this.__initInner();
          }
          document.addEventListener("tetra:before-request", (event) => {
            const css_selector = event.target.getAttribute("tx-indicator");
            if (css_selector) {
              this.$el.querySelectorAll(css_selector).forEach((el) => el.classList.add("tetra-request"));
            } else {
              event.target.classList.add("tetra-request");
            }
          });
          document.addEventListener("tetra:after-request", (event) => {
            const css_selector = event.target.getAttribute("tx-indicator");
            if (css_selector) {
              this.$el.querySelectorAll(css_selector).forEach((el) => el.classList.remove("tetra-request"));
            } else {
              event.target.classList.remove("tetra-request");
            }
          });
        },
        destroy() {
          this.$dispatch("tetra:child-component-destroy", { component: this });
          if (this.__subscribedGroups) {
            this.__subscribedGroups.forEach((group) => {
              this._unsubscribe(group);
            });
          }
          if (this.__destroyInner) {
            this.__destroyInner();
          }
        },
        // Tetra built ins:
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
          this.$dispatch("tetra:component-updated", { component: this });
        },
        _updateData(data) {
          for (const key in data) {
            this[key] = data[key];
          }
          this.$dispatch("tetra:component-data-updated", { component: this });
        },
        _setValueByName(name, value) {
          let inputs = document.getElementsByName(name);
          for (let i = 0; i < inputs.length; i++) {
            inputs[i].value = value;
          }
        },
        _removeComponent() {
          this.$dispatch("tetra:component-before-remove", { component: this });
          this.$root.remove();
        },
        _replaceComponent(html) {
          this.$dispatch("tetra:component-before-remove", { component: this });
          this.$root.insertAdjacentHTML("afterend", html);
          this.$root.remove();
          this.$dispatch("tetra:component-updated", { component: this });
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
        _pushUrl(url, replace = false) {
          if (replace) {
            window.history.replaceState(null, "", url);
          } else {
            window.history.pushState(null, "", url);
          }
        },
        _updateSearchParam(param, value) {
          const url = new URL(window.location);
          if (value) {
            url.searchParams.set(param, value);
          } else {
            url.searchParams.delete(param);
          }
          window.history.pushState(null, "", url.toString());
        },
        // Push notification methods
        _subscribe(groupName, autoUpdate = true) {
          if (!this.__subscribedGroups) {
            this.__subscribedGroups = /* @__PURE__ */ new Set();
          }
          this.__subscribedGroups.add(groupName);
          return Tetra.sendWebSocketMessage({
            type: "subscribe",
            group: groupName,
            component_id: this.component_id,
            component_class: this.componentName,
            auto_update: autoUpdate
          });
        },
        _unsubscribe(groupName) {
          if (this.__subscribedGroups) {
            this.__subscribedGroups.delete(groupName);
          }
          return Tetra.sendWebSocketMessage({
            type: "unsubscribe",
            group: groupName,
            component_id: this.component_id
          });
        },
        _notifyGroup(groupName, eventName, data) {
          return Tetra.sendWebSocketMessage({
            type: "notify",
            group: groupName,
            event_name: eventName,
            data,
            sender_id: this.component_id
          });
        },
        // Tetra private:
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
      Alpine.data(
        componentName,
        (initialDataJson) => {
          const { init, destroy, ...script_rest } = script;
          const initialData = Tetra.jsonDecode(initialDataJson);
          const data = {
            componentName,
            __initInner: init,
            __destroyInner: destroy,
            __serverMethods: serverMethods,
            __serverProperties: serverProperties,
            ...initialData || {},
            ...script_rest,
            ...Tetra.makeServerMethods(serverMethods),
            ...Tetra.alpineComponentMixins()
          };
          return data;
        }
      );
    },
    getStateWithChildren(component) {
      const data = {};
      component.__serverProperties.forEach((key) => {
        data[key] = component[key];
      });
      const r = {
        encrypted: component.__state,
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
    getFilenameFromContentDisposition(contentDisposition) {
      if (!contentDisposition) return null;
      let matches = /filename\*=([^']*)'([^']*)'([^;]*)/i.exec(contentDisposition);
      if (matches) {
        try {
          return decodeURIComponent(matches[3]);
        } catch (e) {
          console.warn("Error decoding filename:", e);
        }
      }
      matches = /filename=["']?([^"';\n]*)["']?/i.exec(contentDisposition);
      if (matches) {
        return matches[1];
      }
      return null;
    },
    async handleServerMethodResponse(response, component) {
      if (response.status === 200) {
        if (response.headers.get("T-Response") !== "true") {
          throw new Error("Response is not a Tetra response. Please check the server implementation.");
        }
        const messages = Tetra.jsonDecode(response.headers.get("T-Messages"));
        if (messages) {
          messages.forEach((message, index) => {
            component.$dispatch("tetra:new-message", message);
          });
        }
        const cd = response.headers.get("Content-Disposition");
        if (cd == null ? void 0 : cd.startsWith("attachment")) {
          const a = document.createElement("a");
          a.href = URL.createObjectURL(await response.blob());
          a.download = this.getFilenameFromContentDisposition(cd);
          a.click();
          a.remove();
          return;
        }
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
    async callServerMethod(component, methodName, methodEndpoint, args) {
      let component_state = Tetra.getStateWithChildren(component);
      component_state.args = args || [];
      let payload = {
        method: "POST",
        headers: {
          "T-Request": "true",
          "T-Current-URL": document.location.href,
          "X-CSRFToken": window.__tetra_csrfToken
        },
        mode: "same-origin"
      };
      let formData = new FormData();
      let hasFiles = false;
      for (const [key, value] of Object.entries(component_state.data)) {
        if (value instanceof File) {
          hasFiles = true;
          component_state.data[key] = {};
          formData.append(key, value);
        }
      }
      if (hasFiles) {
        formData.append("component_state", Tetra.jsonEncode(component_state));
        payload.body = formData;
      } else {
        payload.body = Tetra.jsonEncode(component_state);
        payload.headers["Content-Type"] = "application/json";
      }
      component.$dispatch("tetra:before-request", { component: this });
      const response = await fetch(methodEndpoint, payload);
      component.$dispatch("tetra:after-request", { component: this });
      return await this.handleServerMethodResponse(response, component);
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
      return JSON.parse(s, Tetra.jsonReviver);
    },
    debounce(func, wait, immediate) {
      var timeout;
      return function() {
        var context = this, args = arguments;
        var later = function() {
          timeout = null;
          if (!immediate) func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
      };
    },
    throttle(func, wait, options) {
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
        var _now = (/* @__PURE__ */ new Date()).getTime();
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
  };
  var tetra_core_default = Tetra;

  // tetra/js/tetra.js
  window.Tetra = tetra_core_default;
  window.document.addEventListener("alpine:init", () => {
    tetra_core_default.init();
  });
})();
//# sourceMappingURL=tetra.js.map
