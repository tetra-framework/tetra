(() => {
  // src/tetra/js/tetra.core.js
  var Tetra = {
    ws: null,
    pendingSubscriptions: /* @__PURE__ */ new Map(),
    // Store subscriptions until WS is ready
    init() {
      Alpine.magic("static", () => Tetra.$static);
      if (window.__tetra_useWebsockets) {
        this.ensureWebSocketConnection();
      }
      if (window.__tetra_messages) {
        this.handleInitialMessages(window.__tetra_messages);
        delete window.__tetra_messages;
      }
    },
    handleInitialMessages(messages) {
      messages.forEach((message) => {
        document.dispatchEvent(new CustomEvent("tetra:new-message", {
          detail: message,
          bubbles: true
        }));
      });
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
      let messageType;
      let payload;
      let metadata = {};
      if (data.protocol !== "tetra-1.0") {
        console.warn("Invalid or missing Tetra protocol in WebSocket message:", data);
        return;
      }
      messageType = data.type;
      payload = data.payload;
      metadata = data.metadata || {};
      switch (messageType) {
        case "subscription.response":
          this.handleSubscriptionResponse(payload);
          break;
        case "notify":
          this.handleGroupNotify(payload);
          break;
        case "component.update_data":
          this.handleComponentUpdateData(payload);
          break;
        case "component.remove":
          this.handleComponentRemove(payload);
          break;
        default:
          console.warn("Unknown WebSocket message type:", messageType, ":", data);
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
        case "resubscribed":
          console.debug("Re-subscription to group", event["group"], "successful.");
          document.dispatchEvent(new CustomEvent(`tetra:component-resubscribed`, {
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
          this._handleAutofocus();
          const addClassToExternalIndicators = () => {
            const elementsWithIndicator = [this.$el, ...Array.from(this.$el.querySelectorAll("[t-indicator]"))];
            elementsWithIndicator.forEach((el) => {
              const indicators = el.getAttribute("t-indicator");
              if (indicators) {
                document.querySelectorAll(indicators).forEach((indicator) => {
                  if (indicator.getAttribute("hidden") === null) {
                    indicator.hidden = true;
                  }
                  indicator.classList.add("tetra-indicator-" + this.component_id);
                });
              }
            });
          };
          addClassToExternalIndicators();
          this.$el.addEventListener("tetra:component-updated", addClassToExternalIndicators);
          const handleRequestEvent = (event, isBefore) => {
            const triggerEl = event.detail.triggerEl || event.target;
            const requestId = event.detail.requestId;
            if (!this.$el.contains(triggerEl) && this.$el !== triggerEl) return;
            if (!this.__activeRequests) {
              this.__activeRequests = /* @__PURE__ */ new Map();
            }
            if (isBefore) {
              let triggerSelector = "";
              if (triggerEl.id) {
                triggerSelector = "#" + triggerEl.id;
              }
              this.__activeRequests.set(requestId, {
                triggerSelector,
                indicatorSelector: triggerEl.getAttribute("t-indicator")
              });
            } else {
              this.__activeRequests.delete(requestId);
            }
            const updateElementState = (el, reqId, isStart) => {
              if (!el.__activeRequests) el.__activeRequests = /* @__PURE__ */ new Set();
              if (isStart) el.__activeRequests.add(reqId);
              else el.__activeRequests.delete(reqId);
              return el.__activeRequests.size > 0;
            };
            const hasActive = updateElementState(triggerEl, requestId, isBefore);
            triggerEl.classList.toggle("tetra-request", hasActive);
            const selector = triggerEl.getAttribute("t-indicator");
            if (selector) {
              const localIndicators = Array.from(this.$el.querySelectorAll(selector));
              const globalIndicators = Array.from(document.querySelectorAll(".tetra-indicator-" + this.component_id));
              const allIndicators = new Set(localIndicators);
              globalIndicators.forEach((el) => {
                if (el.matches(selector)) {
                  allIndicators.add(el);
                }
              });
              allIndicators.forEach((el) => {
                const active = updateElementState(el, requestId, isBefore);
                if (active) {
                  el.removeAttribute("hidden");
                  el.hidden = false;
                } else {
                  el.setAttribute("hidden", "");
                  el.hidden = true;
                }
              });
            }
          };
          const reapplyLoadingState = () => {
            if (!this.__activeRequests || this.__activeRequests.size === 0) return;
            this.__activeRequests.forEach((info, reqId) => {
              if (info.triggerSelector) {
                const triggers = this.$el.querySelectorAll(info.triggerSelector);
                triggers.forEach((el) => {
                  if (!el.__activeRequests) el.__activeRequests = /* @__PURE__ */ new Set();
                  el.__activeRequests.add(reqId);
                  el.classList.add("tetra-request");
                });
              }
              if (info.indicatorSelector) {
                const localIndicators = Array.from(this.$el.querySelectorAll(info.indicatorSelector));
                const globalIndicators = Array.from(document.querySelectorAll(".tetra-indicator-" + this.component_id));
                const allIndicators = new Set(localIndicators);
                globalIndicators.forEach((el) => {
                  if (el.matches(info.indicatorSelector)) {
                    allIndicators.add(el);
                  }
                });
                allIndicators.forEach((el) => {
                  if (!el.__activeRequests) el.__activeRequests = /* @__PURE__ */ new Set();
                  el.__activeRequests.add(reqId);
                  el.removeAttribute("hidden");
                  el.hidden = false;
                });
              }
            });
          };
          this.$el.addEventListener("tetra:before-request", (event) => handleRequestEvent(event, true));
          this.$el.addEventListener("tetra:after-request", (event) => handleRequestEvent(event, false));
          this.$el.addEventListener("tetra:component-updated", reapplyLoadingState);
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
          this._handleAutofocus();
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
          this._handleAutofocus();
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
        _handleAutofocus() {
          this.$nextTick(() => {
            if (!this.$root) {
              return;
            }
            const focus_el = this.$root.querySelector("[autofocus]");
            if (focus_el) {
              focus_el.focus();
            }
          });
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
        const cd = response.headers.get("Content-Disposition");
        if (cd == null ? void 0 : cd.startsWith("attachment")) {
          const a = document.createElement("a");
          a.href = URL.createObjectURL(await response.blob());
          a.download = this.getFilenameFromContentDisposition(cd);
          a.click();
          a.remove();
          return;
        }
        const responseText = await response.text();
        const respData = Tetra.jsonDecode(responseText);
        let success = false;
        let result = null;
        let js = [];
        let styles = [];
        let messages = [];
        let callbacks = [];
        if (respData.protocol !== "tetra-1.0") {
          throw new Error("Invalid or missing Tetra protocol in server response");
        }
        success = respData.success;
        if (respData.payload) {
          result = respData.payload.result;
        }
        if (respData.metadata) {
          js = respData.metadata.js || [];
          styles = respData.metadata.styles || [];
          messages = respData.metadata.messages || [];
          callbacks = respData.metadata.callbacks || [];
        }
        if (!success && respData.error) {
          console.error(`Tetra method error [${respData.error.code}]: ${respData.error.message}`);
          document.dispatchEvent(new CustomEvent("tetra:method-error", {
            detail: {
              component,
              error: respData.error
            }
          }));
        }
        if (messages) {
          messages.forEach((message) => {
            component.$dispatch("tetra:new-message", message);
          });
        }
        if (success) {
          let loadingResources = [];
          js.forEach((src) => {
            if (!document.querySelector(`script[src="${CSS.escape(src)}"]`)) {
              loadingResources.push(Tetra.loadScript(src));
            }
          });
          styles.forEach((src) => {
            if (!document.querySelector(`link[href="${CSS.escape(src)}"]`)) {
              loadingResources.push(Tetra.loadStyles(src));
            }
          });
          await Promise.all(loadingResources);
          if (callbacks) {
            callbacks.forEach((item) => {
              let obj = component;
              item.callback.forEach((name, i) => {
                if (i === item.callback.length - 1) {
                  obj[name](...item.args);
                } else {
                  obj = obj[name];
                }
              });
            });
          }
          return result;
        } else {
          if (respData.error) {
            throw new Error(`Error processing public method: ${respData.error.message}`);
          }
          throw new Error("Error processing public method");
        }
      } else {
        throw new Error(`Server responded with an error ${response.status} (${response.statusText})`);
      }
    },
    async callServerMethod(component, methodName, methodEndpoint, args) {
      const requestId = Math.random().toString(36).substring(2, 15);
      let component_state = Tetra.getStateWithChildren(component);
      component_state.args = args || [];
      const requestEnvelope = {
        protocol: "tetra-1.0",
        id: requestId,
        type: "call",
        payload: {
          component_id: component.$el.getAttribute("tetra-component-id"),
          method: methodName,
          args: component_state.args,
          state: component_state.data,
          encrypted_state: component_state.encrypted,
          children_state: component_state.children
        }
      };
      let fetchPayload = {
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
          requestEnvelope.payload.state[key] = {};
          formData.append(key, value);
        }
      }
      if (hasFiles) {
        formData.append("tetra_payload", Tetra.jsonEncode(requestEnvelope));
        fetchPayload.body = formData;
      } else {
        fetchPayload.body = Tetra.jsonEncode(requestEnvelope);
        fetchPayload.headers["Content-Type"] = "application/json";
      }
      const triggerEl = component.$event ? component.$event.target : component.$el;
      component.$dispatch("tetra:before-request", {
        component,
        triggerEl,
        requestId
      });
      const response = await fetch(methodEndpoint, fetchPayload);
      component.$dispatch("tetra:after-request", {
        component,
        triggerEl,
        requestId
      });
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
        previous = options.leading === false ? 0 : Date.now();
        timeout = null;
        result = func.apply(context, args);
        if (!timeout) context = args = null;
      };
      var throttled = function() {
        var _now = Date.now();
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

  // src/tetra/js/tetra.js
  window.Tetra = tetra_core_default;
  window.document.addEventListener("alpine:init", () => {
    tetra_core_default.init();
  });
})();
//# sourceMappingURL=tetra.js.map
