Title: Components

# Components

A component is created as a subclass of `BasicComponent` or `Component` and registered to a library with the `@libraryname.register` decorator, see [component libraries](component-libraries).

``` python
# yourapp/components.py
from sourcetypes import django_html, javascript, css
from tetra import Library, Component, public

default = Library()

@default.register
class MyComponent(Component):
    ...
```

Attributes on a component are standard Python types. When the component is rendered, the state of the whole class is saved (using Pickle, see [state security](state-security)) to enable resuming the component with its full state when public method calls are made by the browser.

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

The `load` method is run both when the component initiates *and* after it is resumed from its saved state. Any attributes that are set by the load method are *not* saved with the state. This is to reduce the size of the state and ensure that the state is not stale when resumed.

Arguments are passed to the `load` method from the Tetra [component "`@`" template tag](component-tag). Arguments are saved with the state so that when the component is resumed the `load` method will receive the same values.

Note: Django Models and Querysets are saved as references to your database, not the current 'snapshots', see [state optimisations](state-security#state-optimisations).

``` python
@default.register
class MyComponent(Component):
    ...
    def load(self, a_var):
        self.a_var = a_var
```

## Public attributes

Public attributes are created with `public()`. These are available to the JavaScript in the browser as part of the (Alpine.js data model)[https://alpinejs.dev/globals/alpine-data].

Values must be serialisable via our extended JSON - this includes all standard JSON types as well as `datetime`, `date`, `time`, and `set`. In the browser these translate to `Date` and `Set`.

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

Python public methods can also call JavaScript methods in the browser as callbacks. These are exposed on the `self.client` "callback queue" object. They are executed by the client when it receives the response from the method call.

``` python
@default.register
class MyComponent(Component):
    ...
    @public(update=False)
    def update_specific_data(self):
        self.client.clientMethod('A value')
```

### .watch

Public methods can "watch" public attributes and be called automatically when they change. They can watch multiple attributes by passing multiple names to `.watch()`.

``` python
@default.register
class MyComponent(Component):
    ...
    @public.watch("message")
    def handle_click(self, value, new_value):
        self.a_value = f"Your message is: {message}"
```

### .debounce  & .throttle

 You can add `.debounce(ms)` or `.throttle(ms)` to debounce or throttle the calling of the method.

``` python
@default.register
class MyComponent(Component):
    ...
    @public.watch("message").debounce(200)
    def handle_click(self, value, new_value):
        self.a_value = f"Your message is: {message}"
```

## Templates

The `template` attribute is the Django template for the component in string form. Tetra template tags are automatically made available to your component templates, and all attributes and methods of the component are available in the context.

Components must have a single top level HTML root node.

HTML attributes passed to the component `@` tag are available as `attrs` in the context, this can be unpacked with the [attribute `...` tag](attribute-tag).

The template can contain replaceable `{% block(s) %}`, the `default` block is the target block if no block is specified when including a component in a page with inner content. This is similar to "slots" in other component frameworks. See [passing blocks](component-tag#passing-blocks) for more details.

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
```

## Client side JavaScript

The `script` attribute holds the client side Alpine.js JavaScript for your component. It should use `export default` to export an object forming the [Alpine.js component "Data"](https://alpinejs.dev/globals/alpine-data). This will be extended with your public attributes and methods.

It can contain all standard Alpine methods such as `init`

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
        }
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

> The plan is to add support for PostCSS and tools such as SASS and LESS in future, along with component scoped CSS in future.
