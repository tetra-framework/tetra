---
title: Components
---
# Components

A component is created as a subclass of `BasicComponent` or `Component` and registered to a library by placing it into a library package, see [component libraries](component-libraries.md).

``` python
# yourapp/components/default.py
# or
# yourapp/components/default/__init__.py
from sourcetypes import django_html, javascript, css
from tetra import Component, public

class MyComponent(Component):
    ...
```

Attributes on a component are standard Python types. When the component is rendered, the state of the whole class is saved (using Pickle, see [state security](state-security.md)) to enable resuming the component with its full state when public method calls are made by the browser.

``` python
class MyComponent(Component):
    something:str = 'My string'
    a_value:bool = True
```

As components are standard Python classes you can construct them with any number of methods. These are by default private, and only available on the server and to your template.

``` python
class MyComponent(Component):
    ...
    def do_something(self):
        pass
```

## The `load()` method

The `load` method is run both when the component initiates, *and* after it is resumed from its saved state, e.g. after a [@public method](#public-methods) has finished. **Any attributes that are set within the load method are *not* saved with the state.** This is to reduce the size of the state and ensure that the state is not stale when resumed.

Arguments are passed to the `load` method from the Tetra ["component" template tag](component-tag.md). Arguments are saved with the state so that when the component is resumed the `load` method will receive the same values.

Note: Django Models and Querysets are saved as references to your database, not the current 'snapshots', see [state optimisations](state-security.md#state-optimisations).

If you want to know more how the flow of the attribute data works, see [component life cycle][component-life-cycle.md].

``` python
class MyComponent(Component):
    ...
    def load(self, a_var, *args, **kwargs):
        self.a_var = a_var
```

## Public attributes

Public attributes are created with `public()`. These are available to the JavaScript in the browser as part of the [Alpine.js data model](https://alpinejs.dev/globals/alpine-data).

Values must be serializable via our extended JSON - this includes all standard JSON types as well as `datetime`, `date`, `time`, and `set`. In the browser these translate to `Date` and `Set`.

``` python
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
class MyComponent(Component):
    ...
    @public
    def handle_click(self, value):
        self.a_value = value
```

Public methods can disable the re-rendering by setting `update=False`.

``` python
class MyComponent(Component):
    ...
    @public(update=False)
    def handle_click2(self):
        do_something()
```

Python public methods can also call JavaScript methods in the browser as callbacks. These are exposed on the `self.client` "callback queue" object, see [`client` API](#client-api). They are executed by the client when it receives the response from the method call.

``` python
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
class MyComponent(Component):
    ...
    @public.watch("message")
    def message_change(self, value, old_value, attr):
        self.a_value = f"Your message is: {message}"
```
When the `.watch` decorator is applied, the method receives three parameters:

* `value`: The current value of the attribute
* `old_value`: The old value of the attribute before the change. You can make comparisons here.
* `attr`: The name of the attribute. This is needed if the method is watching more than one attribute.

### .subscribe

Add this if the method should be subscribed to a JavaScript event which is fired in the component (or one of its children and bubbles up).

```python
class MyComponent(Component):
    ...
    @public.subscribe("keyup.shift.enter")
    def shift_enter_pressed(self, event_detail):
        ... # do something

    @public.subscribe("keyup.f9.window")  # this attaches the event listener to the global <html> element
    def fc9_pressed(self, event_detail):
        ... # do something

```

Tetra automatically adds `@<event>=<yourmethod>($event.detail)` to the root element's attrs.

You can even attach the event listener globally by using `.window` or `.document`, see [Alpine.js docs](https://alpinejs.dev/directives/on#window).

The method always receives the *event detail* as a single parameter. 


### .debounce

 You can add `.debounce(ms)` to debounce the calling of the method.

 By default `debounce` is "trailing edge", it will be triggered at the end of the timeout.

 It takes an optional `immediate` boolean argument (i.e. `.debounce(200, immediate=True)`), this changes the implementation to "leading edge" triggering the method immediately.

``` python
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
class MyComponent(Component):
    ...
    @public.watch("message").throttle(200, trailing=True)
    def message_change(self, value, old_value, attr):
        self.a_value = f"Your message is: {message}"
```


### Return values of public methods

Values returned from the method will be transparently passed to the JavaScript caller. This is especially helpful if you are using Alpine.js data on the client:

```django
<div x-data="{ open: False }">
  <button @click="open = check_if_open()">Check</button>
  <div x-show="open">...</div>
</div>
```

## Templates

### Template types

Tetra components supports two different template types:

#### Inline string templates

If the component has a `template` attribute, it is used as Django template for the component in string form.
Tetra template tags are automatically made available to your inline templates, and all attributes and methods of the
component are available in the context.

#### File templates

When using directory-style components, you can load templates from separate files too. See [Directory style components](component-libraries.md#directory-style-components).

### Generic component template hints

Components must have a single top level HTML root node (you may optionally place an HTML comment in front of it).

HTML attributes passed to the `component` tag are available as `attrs` in the context, this can be unpacked with the [attribute `...` tag](attribute-tag.md).

The template can contain overridable `{% slot(s) %}`, the `default` slot is the target slot if no slot is specified when including a component in a page with inner content. See [slots](slots.md) for more details.

!!! note
    * In VS Code, you can use the [Python Inline Source Syntax Highlighting](https://marketplace.visualstudio.com/items?itemName=samwillis.python-inline-source) VS Code extension to syntax highlight the inline HTML, CSS and JavaScript in your component files using type annotations.
    * in PyCharm, use the `# language=html` comment before the template string. This at least enables the HTML highlighting. For Django, the implementation is still missing.

``` python
from sourcetypes import django_html

class MyComponent(Component):
    ...
    # language=html
    template: django_html = """
    <!-- MyComponent -->
    <div {% ... attrs %}>
      <h1>My component</h1>
      <p>{{ message }}</p>
      {% slot default %}{% endslot %}
    </div>
    """
```

You can easily check if a slot is "filled" with content by using `{% if slots.<slot_name> %}`, to
bypass wrapping elements when a slot was not used:

``` django
{% if slots.title or slots.actions %}
<div class="card-header">
  {% if slots.title %}
    <h3 class="card-title">
      {% slot title %}{% endslot %}
    </h3>
  {% endif %}
  {% if slots.actions %}
    <div class="card-actions">
      {% slot actions %}{% endslot %}
    </div>
  {% endif %}
</div>
{% endif %}
```

### The `tetra` context variable

Within a component template, you have access to a variable named `tetra` which provides basically the same functionality as the [`request.tetra`](request.md#requesttetra) object: a consistent interface for accessing current request information, regardless of whether the request is a Tetra request or a standard Django request. It allows Tetra components to be aware of the current "main" request context, no matter if the component was rendered "as tag" in a full page refresh, or updated via AJAX.

`tetra` provides a dictionary, containing:
- `current_url`: The full browser URL of the current "main" request
- `current_url_path`: The path component of the current URL in the browser
- `current_url_full_path`: The full path, including query parameters

Use these variables in any Tetra component template:

```django
<a href="books/{{ id }}?next={{ tetra.current_full_path|urlencode }}">{{ book_title }}</a>
```

rendered on `/books?author=me` will render to:

```html
<a href="books/1?next=/books%3Fauthor%3Dme"></a>
```

This is particularly useful for:
- Building dynamic navigation, where "back" links should redirect to correct overviews
- Constructing URLs in components that reference the current page
- Debugging and logging purposes

!!! note
    Make sure that the URLs are "urlencoded" if they are meant to be appended to other URLs as parameters.


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

```python
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

It is implemented as a queue that is sent to the client after the public method returns. The client then calls all scheduled callbacks with the provided arguments.

Arguments must be of the same types as our extended JSON, see [public attributes](#public-attributes) for details.

## Built in client methods

There are a number of Tetra built in methods, these are all prefixed with a single underscore so as not to conflict with your own attributes and methods. These can be called both from JavaScript on the client and via the `client` API from the server.

### `_parent` attribute

The `_parent` attribute allows you to access the component's parent component if there is one. Via this you can call methods, both JavaScript and public Python, on an ancestor component:

``` python
class MyComponent(Component):
    ...
    @public(update=False)
    def method_calls_client_method(self):
        # Call a parent method
        self.client._parent.clientMethod('A value')
```

You can chain `_parent` to traverse back up the component tree:

``` python
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
class MyComponent(Component):
    ...
    @public(update=False)
    def my_method(self):
        self.client._redirect('/another-url')
```

This can be combined with [Django's `reverse()`](https://docs.djangoproject.com/en/4.2/ref/urlresolvers/#reverse) function:

``` python
class MyComponent(Component):
    ...
    @public(update=False)
    def my_method(self):
        self.client._redirect(reverse(views.archive))
```

### `_dispatch()`

The `_dispatch` method is a wrapper around the Alpine.js [`dispatch` magic](https://alpinejs.dev/magics/dispatch) allowing you to dispatch events from public server methods. These bubble up the DOM and be captured by listeners on (grand)parent components. It takes an event name as it's first argument, and an extended JSON serialisable object as its second argument. see Alpine.js [`$dispatch`](https://alpinejs.dev/magics/dispatch) for details.

``` python
class MyComponent(Component):
    ...
    @public
    def my_method(self):
        self.client._dispatch('my-event', {"some_data": 123})
```

In a (grand)parent component you can subscribe to these events with the Alpine.js [`x-on` or  `@`](https://alpinejs.dev/directives/on) directive, calling both JavaScript or public Python methods:


``` python
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
Tetra also provides a convenient event subscription shortcut: The [`@public.subscribe("event_name")` decorator](#.subscribe):

You can use all event modifiers [supported by Alpine](https://alpinejs.dev/directives/on#the-event-object), or even subscribe to "global" events by using Alpine's `.window` or `.document` modifiers:

``` html
<div {% ... attrs %}
    @keyup.shift.enter.window="shiftenter_pressed_anywhere($event)"
>
```

### `_removeComponent()`

the `_removeComponent` method removed the component from the DOM and destroys it. This is useful when deleting an item on the server and wanting to remove the corresponding component in the browser:

``` python
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

### `push_url(url)`

Pushes a given URL to the URL bar of your browser. This adds the URL to the browser history, so "back buttons" would work.

Mind the note for URL changes below!

### `replace_url(url)`

Replaces the current browser URL with the new one. This method does not add the URL to the browser history, it just replaces it. 

Mind the note for URL changes below!

### `update_search_param(param, value)`

Updates the current search parameters of the url with a new value. If your URL looks like this: `example.com/foo?tab=main` you can call `update_search_param("q", "23")` which changes the URL immediately to `example.com/foo?tab=main&q=23`.
Another `update_search_param("tab", "orders")` -> `example.com/foo?tab=orders&q=23`.
A `update_search_param("tab")` deletes the `tab` parameter.

!!! note
    If you use the methods above to change URLs in the browser, Tetra is smart enough to recognize the URL has changed, before it reaches the client, so component rendering within the current request can already use the new URL in `request.tetra.current_url[[_full]_path]`.
    Don't use `self.client._pushUrl()` etc. directly., as the URL update happens in the browser, and the component rendering before uses the old URL then.
    
### `calculate_attrs(component_method_finished: bool)`

This hook is called when the component is fully loaded, just 
1. before the state of a component is restored, `load()` was called, immediately before user interactions happen using component methods, and 
2. just before rendering, after all user interactions

You can do some further data updates here that should override all other rules - especially automatically 
updates of attributes can be calculated here, like a "dirty" flag of a form component, or an update of
an attribute that needs to be calculated from other attributes. 
As example, this method is e.g. used in [FormComponent](form-components.md) to clear form errors if the form was not yet submitted.

Attributes:
    `component_method_finished` is `False` when the hook is called before the component method has finished, and `True` afterwords.

```python
class SignupForm(FormComponent):
    ...
    def calculate_attrs(self, component_method_finished):
        # people that pay more than 20 bucks per month may be anonymous.
        if component_method_finished:  # only calculate once, when user methods are done
            self._form.fields["name"].required = self.pay_sum_per_month >= 20
```


## Combining Alpine.js and backend methods

Alpine functionality and Tetra components' backend methods can bee freely combined, so you can use the advantages of
each of them.

This code creates a password input control with an inline "Show/Hide password" button. This is done using Alpine.js, just
on the client - it would use too much overhead to send a request to the server just for toggling a password view. But
additionally, the component calls the server side check method to monitor if the user has entered a valid password.

```python
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

