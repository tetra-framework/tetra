
const Tetra = {
  ws: null,
  pendingSubscriptions: new Map(), // Store subscriptions until WS is ready

  init() {
    Alpine.magic('static', () => Tetra.$static);
    // Initialize WebSocket connection immediately, if in use
    if(window.__tetra_useWebsockets) {
      this.ensureWebSocketConnection();
    }
    // Handle initial messages passed from the server
    if (window.__tetra_messages) {
      this.handleInitialMessages(window.__tetra_messages);
      delete window.__tetra_messages;
    }

    // Initialize global subscription store
    if (!Alpine.store('tetra_subscriptions')) {
      Alpine.store('tetra_subscriptions', {});
    }
  },
  handleInitialMessages(messages) {
    // We need to wait for Alpine components to be ready before dispatching events to them.
    // However, since we use 'defer' for tetra.js and Alpine, they should be ready around the same time.
    // To be safe, we can use Alpine.nextTick or a small timeout if needed, but 
    // usually dispatching on document should work if components listen there.
    messages.forEach((message) => {
      document.dispatchEvent(new CustomEvent('tetra:new-message', {
        detail: message,
        bubbles: true
      }));
    });
  },
  $static() {
    return (path) => {
      return window.__tetra_staticRoot + path;
    }
  },
  // Add WebSocket management methods
  ensureWebSocketConnection() {
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      console.log("Connecting to Tetra WebSocket...");
      const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
      const ws_url = `${ws_scheme}://${window.location.host}/ws/tetra/`;
      this.ws = new WebSocket(ws_url);

      this.ws.onopen = () => {
        console.debug('Tetra WebSocket connected');
        // Process any pending subscriptions
        this.pendingSubscriptions.forEach((data, componentId) => {
          this.ws.send(JSON.stringify(data));
        });
        this.pendingSubscriptions.clear();
      };

      this.ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // Dispatch to all reactive components
        // document.dispatchEvent(new CustomEvent('tetra:push-message', {detail: data}));
        this.handleWebsocketMessage(data);
      };

      this.ws.onclose = () => {
        console.log('Tetra WebSocket disconnected');
        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
          this.ensureWebSocketConnection();
        }, 3000);
      };

      this.ws.onerror = (error) => {
        console.error('Tetra WebSocket error:', error);
      };
    }
    return this.ws;
  },
  _get_component_by_id(component_id) {
    // Find the component by ID and return it
    const componentEl = document.querySelector(`[tetra-component-id="${component_id}"]`);
    if (!componentEl) {
      // silently return undefined if no component with that id was found.
      return;
    }
    return Alpine.$data(componentEl);
  },
  _get_components_by_subscribe_group(group) {
    // Find all components by subscribe topic and return them
    const store = Alpine.store('tetra_subscriptions');
    const componentIds = store[group] || [];
    // Ensure we return a unique list of component data objects that actually exist in DOM
    const components = componentIds.map(id => {
      const c = this._get_component_by_id(id);
      return c;
    }).filter(c => !!c && typeof c._removeComponent === 'function');
    return [...new Set(components)];
  },
  handleWebsocketMessage(data) {
    // This function centrally handles incoming websocket data and dispatches it to the
    // corresponding methods, if necessary.

    let messageType;
    let payload;
    let metadata = {};

    if (data.protocol !== "tetra-1.0") {
      console.warn('Invalid or missing Tetra protocol in WebSocket message:', data);
      return;
    }

    messageType = data.type;
    payload = data.payload;
    metadata = data.metadata || {};

    switch (messageType) {
      case 'subscription.response':
        this.handleSubscriptionResponse(payload);
        break;

      case 'notify':
        this.handleGroupNotify(payload);
        break;

      case 'component.data_changed':
        this.handleComponentDataChanged(payload);
        break;

      case 'component.removed':
        this.handleComponentRemoved(payload);
        break;

      case 'component.created':
        this.handleComponentCreated(payload);
        break;

      default:
        console.warn('Unknown WebSocket message type:', messageType, ":", data);
    }
  },
  handleSubscriptionResponse(event){
    switch(event["status"]) {
      case "subscribed":
        console.debug("Subscription to group", event["group"], "successful.")
        document.dispatchEvent(new CustomEvent(`tetra:component-subscribed`,  {
          detail: {
            component: this,
            group: event["group"]
          },
        }))
        break;
      case "unsubscribed":
        console.debug("Subscription to group", event["group"], "redacted successfully.")
        document.dispatchEvent(new CustomEvent(`tetra:component-unsubscribed`,  {
          detail: {
            component: this,
            group: event["group"]
          },
        }))
        break;
      case "resubscribed":
        console.debug("Re-subscription to group", event["group"], "successful.")
        document.dispatchEvent(new CustomEvent(`tetra:component-resubscribed`,  {
          detail: {
            component: this,
            group: event["group"]
          },
        }))
        break;
      case "error":
        console.error("Error subscribing component", event["component_id"], "to group", event["group"], ":", event["message"])
        document.dispatchEvent(new CustomEvent(`tetra:component-subscription-error`,  {
          detail: {
            component: this,
            group: event["group"],
            message:event["message"]
          },
        }))
        break;
      default:
        console.debug("Subscription response faulty:", event)
    }
  },
  handleGroupNotify(event) {
    /// Dispatch a custom event that was sent from the server as notification
    const { group, event_name, data } = event;

    // Dispatch group-specific event
    document.dispatchEvent(new CustomEvent(event_name, {
      detail: {
        data,
        group,
      }
    }));
  },
  handleComponentDataChanged(event) {
    const { group, data, sender_id } = event;
    const components = this._get_components_by_subscribe_group(group);
    if (components.length === 0) {
        const els = document.querySelectorAll(`[tetra-subscription*="${group}"]`);
        els.forEach(el => {
            const component = Alpine.$data(el);
            if (component && !components.includes(component)) {
                components.push(component);
            }
        });
    }

    // iter through components and update their data fields
    components.forEach((component) => {
      // Skip update if this component is currently waiting for a response
      // from the request that triggered this server-side change.
      if (
        sender_id &&
        component.__activeRequests &&
        component.__activeRequests.has(sender_id)
      ) {
        return;
      }
      if (data && Object.keys(data).length > 0) {
        component._updateData(data);
      } else {
        component._refresh();
      }
    });
  },
  handleComponentRemoved(event) {
    const { type, group, component_id, target_group, sender_id } = event;

    if (component_id) {
      const component = this._get_component_by_id(component_id)

      if (component && component._removeComponent) {
        if (
          sender_id &&
          component.__activeRequests &&
          component.__activeRequests.has(sender_id)
        ) {
          return;
        }
        component._removeComponent();
      }
      return;
    }

    if (target_group) {
      const components = this._get_components_by_subscribe_group(target_group);
      if (components.length === 0) {
        const els = document.querySelectorAll(`[tetra-subscription*="${target_group}"]`);
        els.forEach(el => {
          const component = Alpine.$data(el);
          if (component && component._removeComponent) {
            component._removeComponent();
          }
        });
      }
      components.forEach(component => {
        if (component && component._removeComponent) {
          if (
            sender_id &&
            component.__activeRequests &&
            component.__activeRequests.has(sender_id)
          ) {
            return;
          }
          component._removeComponent();
        }
      });
      return;
    }

    // Fallback: If no component_id or target_group is provided, find all 
    // components subscribed to the group and remove them.
    const components = this._get_components_by_subscribe_group(group);
    if (components.length === 0) {
      const els = document.querySelectorAll(`[tetra-subscription*="${group}"]`);
      els.forEach(el => {
        const component = Alpine.$data(el);
        if (component && component._removeComponent) {
          component._removeComponent();
        }
      });
    }
    components.forEach(component => {
      if (component && component._removeComponent) {
        if (
          sender_id &&
          component.__activeRequests &&
          component.__activeRequests.has(sender_id)
        ) {
          return;
        }
        component._removeComponent();
      }
    });
  },
  handleComponentCreated(event) {
    const { group, data, component_id, target_group, sender_id } = event;
    const components = this._get_components_by_subscribe_group(group);
    components.forEach((component) => {
      if (
        sender_id &&
        component.__activeRequests &&
        component.__activeRequests.has(sender_id)
      ) {
        return;
      }
      if (typeof component._refresh === 'function') {
        component._refresh();
      } else {
        component._updateHtml();
      }
    });
  },
  sendWebSocketMessage(message) {
    if (!this.ws) {
      console.log("WebSocket is not connected. Cannot send message.");
      return
    }
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // Store subscription messages until connection is ready
      if (message.type === 'subscribe' && message.component_id) {
        this.pendingSubscriptions.set(message.component_id, message);
      }
      // Queue other messages
      this.ws.addEventListener('open', () => {
        this.ws.send(JSON.stringify(message));
      }, { once: true });
    }
  },
  alpineComponentMixins() {
    return {
      // Alpine.js lifecycle:
      init() {
        this.component_id = this.$el.getAttribute('tetra-component-id');
        this.$dispatch('tetra:child-component-init', {component:  this});
        // Set component ID attribute on DOM element for targeting
        this.__initServerWatchers();
        this.__initStores();

        // Auto-subscribe if component is reactive
        if (window.__tetra_useWebsockets && this.$el.hasAttribute('tetra-reactive')) {
          Tetra.ensureWebSocketConnection();

          // Handle dynamic subscriptions from template

          const group = this.$el.getAttribute('tetra-subscription');
          if (group) {
            this._subscribe(group);
          }
        }

        if (this.__initInner) {
          this.__initInner();
        }

        this._handleAutofocus();

        const addClassToExternalIndicators = () => {
          // adds `tetra-indicator` class to all elements targeted with `t-indicator` attribute
          const elementsWithIndicator = [this.$el, ...Array.from(this.$el.querySelectorAll('[t-indicator]'))]
          elementsWithIndicator.forEach(el => {
            const indicators = el.getAttribute('t-indicator')
            if (indicators) {
              // If an explicit selector is given, hide it and add marker class to find it later
              document.querySelectorAll(indicators).forEach(indicator => {
                if (indicator.getAttribute('hidden') === null) {
                  // indicator.setAttribute('hidden', '');
                  indicator.hidden = true;
                }
                indicator.classList.add('tetra-indicator-' + this.component_id);
              });
            }
          });
        };
        addClassToExternalIndicators();
        this.$el.addEventListener('tetra:component-updated', addClassToExternalIndicators);

        const handleRequestEvent = (event, isBefore) => {
          const triggerEl = event.detail.triggerEl || event.target;
          const requestId = event.detail.requestId;

          if (!this.$el.contains(triggerEl) && this.$el !== triggerEl) return;

          if (!this.__activeRequests) {
            this.__activeRequests = new Map();
          }

          if (isBefore) {
            let triggerSelector = '';
            if (triggerEl.id) {
              triggerSelector = '#' + triggerEl.id;
            }
            this.__activeRequests.set(requestId, {
              triggerSelector: triggerSelector,
              indicatorSelector: triggerEl.getAttribute('t-indicator'),
              completed: false,
            });
          } else {
            const request = this.__activeRequests.get(requestId);
            if (request) {
              request.completed = true;
            }
            // We keep it in the map for a short while after the request is "completed"
            // to allow handleComponentUpdateData to catch late-arriving WS messages.
            setTimeout(() => {
              this.__activeRequests.delete(requestId);
            }, 500);
          }

          const updateElementState = (el, reqId, isStart) => {
            if (!el.__activeRequests) el.__activeRequests = new Set();
            if (isStart) el.__activeRequests.add(reqId);
            else el.__activeRequests.delete(reqId);
            return el.__activeRequests.size > 0;
          }

          const hasActive = updateElementState(triggerEl, requestId, isBefore);
          triggerEl.classList.toggle("tetra-request", hasActive);

          const selector = triggerEl.getAttribute('t-indicator');
          if (selector) {
            const localIndicators = Array.from(this.$el.querySelectorAll(selector))
            const globalIndicators = Array.from(document.querySelectorAll('.tetra-indicator-' + this.component_id))

            const allIndicators = new Set(localIndicators)
            globalIndicators.forEach(el => {
              if (el.matches(selector)) {
                allIndicators.add(el)
              }
            })

            allIndicators.forEach(el => {
              const active = updateElementState(el, requestId, isBefore);
              if (active) {
                el.removeAttribute('hidden');
                el.hidden = false;
              } else {
                el.setAttribute('hidden', '');
                el.hidden = true;
              }
            })
          }
        };

        const reapplyLoadingState = () => {
          if (!this.__activeRequests || this.__activeRequests.size === 0) return;

          this.__activeRequests.forEach((info, reqId) => {
            // ONLY reapply if the request is NOT yet completed.
            // If it is completed, it's only in the Map to block WS updates.
            if (info.completed) return;

            if (info.triggerSelector) {
              const triggers = this.$el.querySelectorAll(info.triggerSelector);
              triggers.forEach(el => {
                if (!el.__activeRequests) el.__activeRequests = new Set();
                el.__activeRequests.add(reqId);
                el.classList.add("tetra-request");
              });
            }
            if (info.indicatorSelector) {
              const localIndicators = Array.from(this.$el.querySelectorAll(info.indicatorSelector))
              const globalIndicators = Array.from(document.querySelectorAll('.tetra-indicator-' + this.component_id))

              const allIndicators = new Set(localIndicators)
              globalIndicators.forEach(el => {
                if (el.matches(info.indicatorSelector)) {
                  allIndicators.add(el)
                }
              })
              
              allIndicators.forEach(el => {
                if (!el.__activeRequests) el.__activeRequests = new Set();
                el.__activeRequests.add(reqId);
                el.removeAttribute('hidden');
                el.hidden = false;
              });
            }
          });
        };

        this.$el.addEventListener("tetra:before-request", (event) => handleRequestEvent(event, true));
        this.$el.addEventListener("tetra:after-request", (event) => handleRequestEvent(event, false));
        this.$el.addEventListener('tetra:component-updated', reapplyLoadingState);
      },
      destroy() {
        this.$dispatch('tetra:child-component-destroy', {component:  this});

        // Unsubscribe from all group when component is destroyed
        if (!this.__isUpdating && this.__subscribedGroups) {
          [...this.__subscribedGroups].forEach(group => {
            this._unsubscribe(group);
          });
        }

        if (this.__destroyInner) {
          this.__destroyInner();
        }
      },
      // Tetra built ins:
      _updateHtml(html) {
        this.__isUpdating = true;
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
        this.__isUpdating = false;

        // Check for subscription changes after morphing
        if (window.__tetra_useWebsockets && this.$el.hasAttribute('tetra-reactive')) {
          const group = this.$el.getAttribute('tetra-subscription');
          const currentTopics = group ? group.split(',').map(t => t.trim()) : [];
          const oldTopics = this.__subscribedGroups ? Array.from(this.__subscribedGroups) : [];
          
          // Unsubscribe from topics that are no longer present
          oldTopics.forEach(topic => {
            if (!currentTopics.includes(topic)) {
              this._unsubscribe(topic);
            }
          });
          
          // Subscribe to new topics
          currentTopics.forEach(topic => {
            if (!this.__subscribedGroups || !this.__subscribedGroups.has(topic)) {
              this._subscribe(topic);
            }
          });
        }

        this._handleAutofocus();
        this.$dispatch('tetra:component-updated', { component: this });
      },
      _updateData(data) {
        let activeEl = document.activeElement;
        let focusedModel = null;
        if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT') && this.$el.contains(activeEl)) {
          // Check if the focused element is bound to a model
          focusedModel = activeEl.getAttribute('x-model');
          if (!focusedModel) {
            // also check for x-model on parent elements, up to the component root
            let el = activeEl.parentElement;
            while (el && el !== this.$el && !focusedModel) {
              focusedModel = el.getAttribute('x-model');
              el = el.parentElement;
            }
          }
        }

        for (const key in data) {
          if (focusedModel === key) {
            console.debug(`Skipping update for focused field: ${key}`);
            continue;
          }
          this[key] = data[key];
        }
        // this._handleAutofocus(); // TODO: evaluate if this would make sense too
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
        this.__isUpdating = true;
        this.$dispatch('tetra:component-before-remove', { component: this });
        this.$root.insertAdjacentHTML('afterend', html);
        this.$root.remove();
        this.__isUpdating = false;
        this.$dispatch('tetra:component-updated', { component: this });
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
      _pushUrl(url, replace=false) {
        if(replace){
          window.history.replaceState(null, '', url);
        } else {
          window.history.pushState(null, '', url);
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
      _subscribe(groupName) {
        if (!this.__subscribedGroups) {
          this.__subscribedGroups = new Set();
        }

        const store = Alpine.store('tetra_subscriptions');
        const topics = groupName.split(',').map(t => t.trim());
        
        topics.forEach(topic => {
          this.__subscribedGroups.add(topic);
          
          if (!store[topic]) {
            store[topic] = [];
          }
          
          if (!store[topic].includes(this.component_id)) {
            const isFirst = store[topic].length === 0;
            store[topic].push(this.component_id);

            if (isFirst) {
              Tetra.sendWebSocketMessage({
                type: 'subscribe',
                group: topic,
                component_id: this.component_id,
                component_class: this.componentName,
              });
            }
          }
        });
      },

      _unsubscribe(groupName) {
        if (!this.__subscribedGroups) return;

        const store = Alpine.store('tetra_subscriptions');
        const topics = groupName.split(',').map(t => t.trim());

        topics.forEach(topic => {
          this.__subscribedGroups.delete(topic);
          
          if (store[topic]) {
            const index = store[topic].indexOf(this.component_id);
            if (index > -1) {
              store[topic].splice(index, 1);
              const isLast = store[topic].length === 0;
              if (isLast) {
                delete store[topic];
                Tetra.sendWebSocketMessage({
                  type: 'unsubscribe',
                  group: topic,
                  component_id: this.component_id
                });
              }
            }
          }
        });
      },

      _notifyGroup(groupName, eventName, data) {
        return Tetra.sendWebSocketMessage({
          type: 'notify',
          group: groupName,
          event_name: eventName,
          data: data,
          sender_id: this.component_id
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
      __initStores() {
        if (!this.__serverStores) return;

        Object.entries(this.__serverStores).forEach(([propName, storePath]) => {
          const parts = storePath.split('.');
          const storeName = parts[0];
          const propertyPath = parts.slice(1);

          // Initialize store if it doesn't exist
          if (!Alpine.store(storeName)) {
            Alpine.store(storeName, {});
          }

          const getStoreValue = () => {
            let val = Alpine.store(storeName);
            for (const part of propertyPath) {
              if (val === undefined || val === null || typeof val !== 'object') return undefined;
              val = val[part];
            }
            return val;
          };

          const setStoreValue = (value) => {
            if (propertyPath.length === 0) {
              if (Alpine.store(storeName) !== value) {
                Alpine.store(storeName, value);
              }
            } else {
              let obj = Alpine.store(storeName);
              for (let i = 0; i < propertyPath.length - 1; i++) {
                const part = propertyPath[i];
                if (!(part in obj) || typeof obj[part] !== 'object') obj[part] = {};
                obj = obj[part];
              }
              const lastPart = propertyPath[propertyPath.length - 1];
              if (obj[lastPart] !== value) {
                obj[lastPart] = value;
              }
            }
          };

          // Track previous store value to detect actual store changes
          let prevStoreVal = getStoreValue();

          // Two-way sync: Store -> Component
          Alpine.effect(() => {
            const storeVal = getStoreValue();

            // Only update component if the STORE value actually changed
            if (storeVal !== prevStoreVal && storeVal !== undefined) {
              prevStoreVal = storeVal;
              if (this[propName] !== storeVal) {
                this.__isSyncingFromStore = propName;
                this[propName] = storeVal;
                this.$nextTick(() => {
                  if (this.__isSyncingFromStore === propName) {
                    this.__isSyncingFromStore = null;
                  }
                });
              }
            }
          });

          // Two-way sync: Component -> Store
          this.$watch(propName, (value) => {
            if (this.__isSyncingFromStore !== propName) {
              const currentStoreVal = getStoreValue();
              if (currentStoreVal !== value) {
                setStoreValue(value);
                prevStoreVal = value; // Update tracking after successful store update
              }
            }
          });

          // Initial sync: Check if store already has a value
          const initialStoreVal = getStoreValue();
          if (initialStoreVal !== undefined) {
            // Store already has a value (set by another component)
            // Update component to match the store immediately
            this[propName] = initialStoreVal;
            prevStoreVal = initialStoreVal;
          } else {
            // Store doesn't have a value yet
            // Initialize it with this component's value
            setStoreValue(this[propName]);
            prevStoreVal = this[propName];
          }
        });
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
            __serverStores: initialData?.__serverStores,
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
    if (component.__serverStores) {
      data["__serverStores"] = component.__serverStores;
    }
    const r = {
      encrypted: component.__state,
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
  getFilenameFromContentDisposition(contentDisposition) {
    if (!contentDisposition) return null;

    // First, try to get the filename* parameter (RFC 5987)
    let matches = /filename\*=([^']*)'([^']*)'([^;]*)/i.exec(contentDisposition);
    if (matches) {
      // Decode the UTF-8 encoded filename
      try {
        return decodeURIComponent(matches[3]);
      } catch (e) {
        console.warn('Error decoding filename:', e);
      }
    }
    // Try to get the regular filename parameter
    matches = /filename=["']?([^"';\n]*)["']?/i.exec(contentDisposition);
    if (matches) {
      return matches[1];
    }
    return null;
  },

  async handleServerMethodResponse(response, component) {
    if (response.status === 200) {
      const cd = response.headers.get('Content-Disposition')
      if (cd?.startsWith("attachment")) {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(await response.blob())
        a.download = this.getFilenameFromContentDisposition(cd)
        a.click()
        a.remove()
        return;
      }

      const responseText = await response.text();
      const respData = Tetra.jsonDecode(responseText);

      let success = false;
      let result = null;
      let html = null;
      let js = [];
      let styles = [];
      let messages = [];
      let callbacks = [];

      if (respData.protocol !== "tetra-1.0") {
        throw new Error('Invalid or missing Tetra protocol in server response');
      }

      success = respData.success;
      if (respData.payload) {
        result = respData.payload.result;
        html = respData.payload.html;
      }
      if (respData.metadata) {
        js = respData.metadata.js || [];
        styles = respData.metadata.styles || [];
        messages = respData.metadata.messages || [];
        callbacks = respData.metadata.callbacks || [];

        // Fast lane for redirects
        const redirectCallback = callbacks.find(item =>
            item.callback && item.callback.length === 1 && item.callback[0] === '_redirect'
        );
        if (redirectCallback && redirectCallback.args && redirectCallback.args.length > 0) {
          document.location = redirectCallback.args[0];
          return;
        }
      }
      if (!success && respData.error) {
        console.error(`Tetra method error [${respData.error.code}]: ${respData.error.message}`);
        // Emit event for custom error handling
        document.dispatchEvent(new CustomEvent('tetra:method-error', {
          detail: {
            component: component,
            error: respData.error
          }
        }));
      }

      // handle Django messages and emit "tetra:new-message" for each one
      if (messages) {
        messages.forEach((message) => {
          component.$dispatch('tetra:new-message', message)
        })
      }

      if (success) {
        let loadingResources = [];
        js.forEach(src => {
          if (!document.querySelector(`script[src="${CSS.escape(src)}"]`)) {
            loadingResources.push(Tetra.loadScript(src));
          }
        })
        styles.forEach(src => {
          if (!document.querySelector(`link[href="${CSS.escape(src)}"]`)) {
            loadingResources.push(Tetra.loadStyles(src));
          }
        })
        await Promise.all(loadingResources);

        if (html) {
          component._updateHtml(html);
        }

        if (callbacks) {
          callbacks.forEach((item) => {
            // iterate down path to callback
            let obj = component;
            item.callback.forEach((name, i) => {
              if (i === item.callback.length-1) {
                obj[name](...item.args);
              } else {
                obj = obj[name];
              }
            })
          })
        }
        return result;
      } else {
        if (respData.error) {
          throw new Error(`Error processing public method: ${respData.error.message}`);
        }
        throw new Error('Error processing public method');
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
        component_id: component.$el.getAttribute('tetra-component-id'),
        method: methodName,
        args: component_state.args,
        state: component_state.data,
        encrypted_state: component_state.encrypted,
        children_state: component_state.children
      }
    };

    let fetchPayload = {
      method: 'POST',
      headers: {
        'T-Request': "true",
        'T-Current-URL': document.location.href,
        'X-CSRFToken': window.__tetra_csrfToken,
      },
      mode: 'same-origin',
    }

    let formData = new FormData();
    let hasFiles = false;
    for(const [key, value] of Object.entries(component_state.data)){
      // TODO: handle multi-file uploads
      if (value instanceof File) {
        hasFiles = true;
        // A file is not uploaded anyway, as the browser automatically deletes the data if submitted within a JSON.
        // On the server, only an empty {} will arrive, so we can set it to {} anyway.
        // In the protocol, we keep the original state, but when sending we might need to adjust.
        requestEnvelope.payload.state[key] = {};
        formData.append(key, value);
        // TODO: prevent re-uploading of files that are already uploaded.
      }
    }

    // check if FormData has *any* entry - and if not, send JSON request
    if (hasFiles) {
      formData.append('tetra_payload', Tetra.jsonEncode(requestEnvelope));
      fetchPayload.body = formData;
    } else {
      fetchPayload.body = Tetra.jsonEncode(requestEnvelope)
      fetchPayload.headers['Content-Type'] = 'application/json'
    }
    const triggerEl = component.$event ? component.$event.target : component.$el;
    component.$dispatch('tetra:before-request', {
      component: component,
      triggerEl: triggerEl,
      requestId: requestId
    });
    const response = await fetch(methodEndpoint, fetchPayload);
    component.$dispatch('tetra:after-request', {
      component: component,
      triggerEl: triggerEl,
      requestId: requestId
    })
    const result = await this.handleServerMethodResponse(response, component);

    // If the request was successful, we might have already updated the data via
    // the HTTP response. We keep the requestId in __activeRequests until now
    // to ensure handleComponentUpdateData can filter it out if it arrives
    // around the same time.
    // However, the 'tetra:after-request' event already removed it from
    // __activeRequests in the default Alpine mixin (if not overridden).
    // Actually, looking at the code, tetra:after-request IS what removes it.

    return result;
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
    // else if (value?.[0] instanceof File) {
    //   return {
    //     __type: 'file',
    //     name: value[0].name,
    //     value: value[0],
    //     size: value[0].size,
    //     content_type: value[0].type,
    //   };
    // }
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

}

export default Tetra;
