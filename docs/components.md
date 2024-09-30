---
title: Components
---
# Components

A component is created as a subclass of `BasicComponent` or `Component` and registered to a library with the `@libraryname.register` decorator, see [component libraries](component-libraries.md).

``` python
# yourapp/components.py
from sourcetypes import django_html, javascript, css
from tetra import Library, Component, public

default = Library()

@default.register
class MyComponent(Component):
    ...
```

Attributes on a component are standard Python types. When the component is rendered, the state of the whole class is saved (using Pickle, see [state security](state-security.md)) to enable resuming the component with its full state when public method calls are made by the browser.

``` python
@default.register
class MyComponent(Component):
    something = 'My string'
    a_value = True
```

As components are standard Python classes you can construct them with any number of methods. These are by default private, and only available on the server and to your template.

``` python
@default.register
class MyComponent(Component):
    ...
    def do_something(self):
        pass
```

## Load method

The `load` method is run both when the component initiates, *and* after it is resumed from its saved state, e.g. after a [@public method](#public-methods) has finished. Any attributes that are set by the load method are *not* saved with the state. This is to reduce the size of the state and ensure that the state is not stale when resumed.

Arguments are passed to the `load` method from the Tetra [component "`@`" template tag](component-tag.md). Arguments are saved with the state so that when the component is resumed the `load` method will receive the same values.

Note: Django Models and Querysets are saved as references to your database, not the current 'snapshots', see [state optimisations](state-security.md#state-optimisations).

``` python
@default.register
class MyComponent(Component):
    ...
    def load(self, a_var):
        self.a_var = a_var
```

## Public attributes

Public attributes are created with `public()`. These are available to the JavaScript in the browser as part of the [Alpine.js data model](https://alpinejs.dev/globals/alpine-data).

Values must be serializable via our extended JSON - this includes all standard JSON types as well as `datetime`, `date`, `time`, and `set`. In the browser these translate to `Date` and `Set`.

``` python
@default.register
class MyComponent(Component):
    ...
    test = public("Initial String")
    message = public("Initial Message")
    a_property = public("Something")
    counter = public(0)
```

## Public methods

The `public` decorator makes "public" methods that are available from JavaScript on the client.

Values passed to, or returned from, public methods must be of the same extended JSON types as public attribute above.

By default, public methods re-render your template and updates the HTML in place in the browser.

``` python
@default.register
class MyComponent(Component):
    ...
    @public
    def handle_click(self, value):
        self.a_value = value
```

Public methods can disable the re-rendering by setting `update=False`.

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def handle_click2(self):
        do_something()
```

Python public methods can also call JavaScript methods in the browser as callbacks. These are exposed on the `self.client` "callback queue" object, see [`client` API](#client-api). They are executed by the client when it receives the response from the method call.

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def update_specific_data(self):
        self.client.clientMethod('A value')
```

### .watch

Public methods can "watch" public attributes and be called automatically when they change.
They can watch multiple attributes by passing multiple names to `.watch()`.

``` python
@default.register
class MyComponent(Component):
    ...
    @public.watch("message")
    def message_change(self, value, old_value, attr):
        self.a_value = f"Your message is: {message}"
```
When the `.watch` decorator is applied, the method receives 3 parameters:

* *value*: The current value of the attribute
* *old_value*: The old value of the attribute before the change. You can make comparisons here.
* *attr*: The name of the attribute. This is needed, if the method is watching more than one attributes.

### .debounce

 You can add `.debounce(ms)` to debounce the calling of the method.

 By default `debounce` is "trailing edge", it will be triggered at the end of the timeout.

 It takes an optional `immediate` boolean argument (i.e. `.debounce(200, immediate=True)`), this changes the implementation to "leading edge" triggering the method immediately.

``` python
@default.register
class MyComponent(Component):
    ...
    @public.watch("message").debounce(200)
    def message_change(self, value, old_value, attr):
        self.a_value = f"Your message is: {message}"
```

!!! note
    On Python versions prior to 3.9 the chained decorator syntax above is invalid
    (see [PEP 614](https://peps.python.org/pep-0614/)).
    On older versions you can apply the decorator multiple times with each method required:

``` python
@default.register
class MyComponent(Component):
    ...
    @public.watch("message")
    @public.debounce(200)
    def message_change(self, value, old_value, attr):
        self.a_value = f"Your message is: {message}"
```

### .throttle

 You can add `.throttle(ms)` to throttle the calling of the method.

 By default `throttle` is "leading edge" triggering immediately. You can instruct it to also trigger on the "trailing edge" by setting argument `trailing=True`. The leading edge trigger can be disabled with `leading=False`.

``` python
@default.register
class MyComponent(Component):
    ...
    @public.watch("message").throttle(200, trailing=True)
    def message_change(self, value, old_value, attr):
        self.a_value = f"Your message is: {message}"
```

## Templates

### Template types

Tetra components supports two different template types:

#### Inline string templates

If the component has a `template` attribute, it is used as Django template for the component in string form.
Tetra template tags are automatically made available to your inline templates, and all attributes and methods of the
component are available in the context.

#### File templates

You can also use the more traditional way and put your HTML code into a separate HTML file. You have to point to this
file using the `template_name` attribute of the component class. Beware that you have to load the `tetra` templatetag
yourself there. This has the advantage of having full syntax highlighting and IDE goodies support in your file which
comes handy for especially bigger templates, but it splits a component a bit up into separate pieces.


### Generic template hints

Components must have a single top level HTML root node.

HTML attributes passed to the component `@` tag are available as `attrs` in the context, this can be unpacked with the [attribute `...` tag](attribute-tag.md).

The template can contain replaceable `{% block(s) %}`, the `default` block is the target block if no block is specified when including a component in a page with inner content. This is similar to "slots" in other component frameworks. See [passing blocks](component-tag.md#passing-blocks) for more details.

You can use the [Python Inline Source Syntax Highlighting](https://marketplace.visualstudio.com/items?itemName=samwillis.python-inline-source) VS Code extension to syntax highlight the inline HTML, CSS and JavaScript in your component files using type annotations.

``` python
@default.register
class MyComponent(Component):
    ...
    template: django_html = """
    <div {% ... attrs %}>
      <h1>My component</h1>
      <p>{{ message }}</p>
      {% block default %}{% endblock %}
    </div>
    """

    # or:
    template_name = "my_app/components/my_component.html"
```

You can easily check if a block is "filled" with content by using `{% if blocks.<block name> %}`. With this, you can
bypass wrapping elements when a block was not used:

``` django
{% if blocks.title or blocks.actions %}
<div class="card-header">
  <h3 class="card-title">
    {% block title %}{% endblock %}
  </h3>
  <div class="card-actions">
    {% block actions %}{% endblock %}
  </div>
</div>
{% endif %}
```

## Extra context

By default, outer template context is not passed down to the component's template when rendering; this is to optimise the size of the saved component state.
If you need a component class to generally receive some context variables, you can set that explicitly using `_extra_context` in the class:

```python
class MyComponent(BasicComponent):
    _extra_context = ["user", "a_context_var"]
    ...
```

This component has access to the global `user` and `a_context_var` variables.
If a component needs the whole context, you can add the "__all__" string instead of a list:

```django
class MyComponent(BasicComponent):
    _extra_context = "__all__"
```

!!! warning
    You want to use `__all__` mostly in `BasicComponent`s which have no saved state.
    It should be used sparingly in a `Component` as the whole template context will be saved with the component's saved (encrypted) state, and sent to the client, see [state security](state-security.md).

Explicitly passed variables [in component tags](component-tag.md#passing-context) will override this behaviour.


## Client side JavaScript

The `script` attribute holds the client side Alpine.js JavaScript for your component. It should use `export default` to export an object forming the [Alpine.js component "Data"](https://alpinejs.dev/globals/alpine-data). This will be extended with your public attributes and methods.

It can contain all standard Alpine methods such as `init`.

Other JavaScript files can be imported using standard `import` syntax relative to the source file.

You can use the `javascript` type annotation for syntax highlighting in VS Code.

``` python
@default.register
class MyComponent(Component):
    ...
    script: javascript = """
    export default {
        init() {
          // Do stuff...
        },
        handleClick() {
            this.message = `Hello ${this.name}`;
        },
        clientMethod(msg) {
          alert(msg)
        }
    }
    """
```

## CSS Styles

The `styles` attribute holds the CSS for your component.

You can use the `css` type annotation for syntax highlighting in VS Code.

``` python
@default.register
class MyComponent(Component):
    ...
    style: css = """
        .a-red-style {
            color: #f00;
        }
    """
```

!!! note
    The plan is to add support for PostCSS and tools such as SASS and LESS in future, along with component scoped CSS in future.


## `client` API

From public methods its possible to call client side javascript via the `.client` API. Any of your JavaScript methods can be called via this api:

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def method_calls_client_method(self):
        self.client.clientMethod('A value')
    
    script: javascript = """
    export default {
        clientMethod(msg) {
          alert(msg)
        }
    }
    """
```

It is implemented as a queue that is sent to the client after thee public method returns. The client they calls all scheduled callbacks with the provided arguments.

Arguments must be of the same types as our extended JSON, see [public attributes](#public-attributes) for details.

## Built in client methods

There are a number of Tetra built in methods, these are all prefixed with a single underscore so as not to conflict with your own attributes and methods. These can be called both from JavaScript on the client and via the `client` API from the server.

### `_parent` attribute

The `_parent` attribute allows you to access the component's parent component if there is one. Via this you can call methods, both JavaScript and public Python, on an ancestor component:

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def method_calls_client_method(self):
        # Call a parent method
        self.client._parent.clientMethod('A value')
```

You can chain `_parent` to traverse back up the component tree:

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def method_calls_client_method(self):
        # Call a grandparent method
        self.client._parent._parent.clientMethod('A value')
```

### `_redirect()`

The `_redirect` method allows you to instruct the client to redirect to another url after calling a public method:

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def my_method(self):
        self.client._redirect('/another-url')
```

This can be combined with [Django's `reverse()`](https://docs.djangoproject.com/en/4.2/ref/urlresolvers/#reverse) function:

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def my_method(self):
        self.client._redirect(reverse(views.archive))
```

### `_dispatch()`

The `_dispatch` method is a wrapper around the Alpine.js [`dispatch` magic](https://alpinejs.dev/magics/dispatch) allowing you to dispatch events from public server methods. These bubble up the DOM and be captured by listeners on (grand)parent components. It takes an event name as it's first argument, and an extended JSON serialisable object as its second argument. see Alpine.js [`$dispatch`](https://alpinejs.dev/magics/dispatch) for details.

``` python
@default.register
class MyComponent(Component):
    ...
    @public
    def my_method(self):
        self.client._dispatch('my-event', {"some_data": 123})
```

In a (grand)parent component you can subscribe to these events with the Alpine.js [`x-on` or  `@`](https://alpinejs.dev/directives/on) directive, calling both JavaScript or public Python methods:


``` python
@default.register
class MyComponent(Component):
    ...
    @public
    def handle_my_event(self, event):
        ...

    template: django_html = """
    <div {% ... attrs %}
        @my-event="handle_my_event($event)"
        @my-event="handleMyEvent($event)"
    >
        ...
    </div>
    """
    
    script: javascript = """
    export default {
        handleMyEvent(event) {
            ...
        }
    }
    """
```

### `_removeComponent()`

the `_removeComponent` method removed the component from the DOM and destroys it. This is useful when deleting an item on the server and wanting to remove the corresponding component in the browser:

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def delete_item(self):
        self.todo.delete()
        self.client._removeComponent()
```

### `_updateData()`

The `_updateData` method allows you to update specific public state data on the client. It takes a `dict` of values to update on the client:

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def update_something(self):
        self.client._updateData({
            "something": 123,
            "somethingElse": 'A string',
        })
```

This can be used to update data on a parent component:

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def update_parent(self):
        self.client._parent._updateData({
            "something": 123,
            "somethingElse": 'A string',
        })
```

## Built in server methods

There are a number of built-in server methods:

### `update()`

The `update` method instructs the component to rerender after the public method has completed, sending the updated HTML to the browser and "morphing" the DOM. Usually public methods do this by default. However, if this has been turned off with `update=False`, and you want to conditionally update the html, you can use this:

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def update_something(self):
        ...
        if some_value:
            self.update()
```

### `update_data()`

The `update_data` method instructs the component to send the complete set of public attribute to the client, updating their values, useful in combination with `@public(update=False)`:

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def update_something(self):
        ... # Do stuff, then
        self.update_data()
```
This way, no component re-rendering in the browser is triggered, just the values itself are updated.

### `replace_component()`

This removes and destroys the component in the browser and re-inserts a new copy into the DOM. Any client side state,
such as cursor location in text inputs will be lost.


### `ready()`

Called when the component is fully loaded, just before rendering. The state is restored, `load()` was called, and data from the frontend was already applied to the backend state.
You can do some further initialization here that should override all other rules; Especially attributes set in `load()` are not saved with the state, and would be lost.
It can be used to add dynamical changing elements to an attached Django form. 

```python
class SignupForm(DynamicFormMixin, FormComponent):
    ...
    def ready(self):
        # people that pay more than 20 bucks per month may be anonymous.
        self._form.fields["name"].required = self.pay_sum_per_month >= 20
```


## Combining Alpine.js and backend methods

Alpine functionality and Tetra components' backend methods can bee freely combined, so you can use the advantages of
each of them.

This code creates a password input control with an inline "Show/Hide password" button. This is done using Alpine.js, just
on the client - it would use too much overhead to send a request to the server just for toggling a password view. But
additionally, the component calls the server side check method to monitor if the user has entered a valid password.

```python
@default.register
class PasswordInput(Component):
    visible: bool = public(False)
    password: str = public("")
    valid: bool = public(True)
    feedback_text: str = ""

    @public.watch("password").debounce(500)
    def check(self, value, old_value, attr_name):
        """Check password validity"""
        if len(value) > 12:
            self.valid = True
            self.feedback_text = "Password has more than 12 chars."
        else:
            self.valid = False
            self.feedback_text = "Error: Password must have more than 12 chars."

    template: django_html = """
    <div>
        <div class="input-group input-group-flat{% if password %}{% if valid %} is-valid{%
            else %} is-invalid {% endif %}{% endif %}"
            :class="valid ? 'is-valid' : 'is-invalid'"
        >
          <input class="form-control"
                 :type="visible ? 'text' : 'password'"
                 x-model="password" />
          <span class="input-group-text">
            <a href="#" class="input-group-link" @click="visible = !visible">
              <span x-text="visible ? 'Hide' : 'Show'"></span>
            </a>
          </span>
        </div>
        <div class="{% if not valid %}in{% endif %}valid-feedback">
        {{ feedback_text }}</div>
    </div>
    """

```

