---
title: Tutorial
---

# A Tetra tutorial - creating a Todo app

We all know that a "hello world" doesn't get anyone excited anymore. So we will guide you step by step through the making of the Todo application of the [main Tetra page](https://tetraframework.com).

*If you haven't used Django before you should follow their [tutorial](https://docs.djangoproject.com/en/4.2/intro/tutorial01/) before coming back here.*



After setting up a Django, we need a "model" for saving our "todo" items:

``` python
# models.py
from django.db import models

class ToDo(models.Model):
    session_key = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=80)
    done = models.BooleanField(default=False)
```

Assuming we have [installed and setup](install.md) Tetra, next we create a `components/default.py` file to contain our components. Every component belongs to a "Library", this is done by putting the component class into a containing module named `default`.

``` python
# components/default.py
from sourcetypes import javascript, css, django_html
from tetra import Component, public, Library
from .models import ToDo
```

### `TodoList` Component

Next, we create a `TodoList` component by subclassing `Component`.

We also create a "public attribute" named `title`; the value of this is available to both your server side code / template *and* to your front end JavaScript / Alpine.js.

There is also a `load` method - this is called both when initially rendering the component, and when the component is "resumed" from its saved state. (More on this later)

``` python
class TodoList(Component):
    title = public("")

    def load(self, *args, **kwargs):
        self.todos = ToDo.objects.filter(session_key=self.request.session.session_key)
```

Next up, we have a "public method"; these are available in the browser to your JavaScript / Alpine.js code. This creates a new `ToDo` model instance, sets its title, and saves it. Finally, the value of the  public `title` attribute is reset to an empty string, which will subsequently empty the input box after saving.

``` python
    @public
    def add_todo(self, title):
        todo = ToDo(
            title=title,
            session_key=self.request.session.session_key,
        )
        todo.save()
        self.title = ""
```

Then there is the template; this uses the standard Django template language. You will note the `django_html` type annotation, which is an  alias of  `str` and indicates to your editor to syntax highlight the following string. There is a [VS Code extension](https://marketplace.visualstudio.com/items?itemName=samwillis.python-inline-source) available.

``` python
    template: django_html = """
    <div>
        <div class="input-group mb-2">
            <input type="text" x-model="title" class="form-control" 
                placeholder="New task..." @keyup.enter="add_todo(title)">
            <button class="btn btn-primary" @click="add_todo(title)">Add</button>
        </div>
        <div class="list-group">
            {% for todo in todos %}
                {% TodoItem todo=todo key=todo.id / %}
            {% endfor %}
        </div>
    </div>
    """
```

- The public `title` attribute is bound to the input value using the Alpine.js `x-model` directive.
- An Alpine.js `@keyup.enter` event listener is attached to the input, calling our `add_todo` public method when the user presses enter within the input.
- Another `@click` event listener is attached to the button, also calling our `add_todo` public method.
- A standard Django template `for` loop iterates through any 'to do' items loaded to the private `todos` attribute (see our `load` method above).
- We use the Tetra `@` component template tag to display the `to_do_item` component. We pass it a `todo` model instance as an argument, and a `key` argument set to the `todo.id`. It is  important to "key" components in loops so that when morphing the DOM they are correctly identified and updated.
- The `TodoItem` component tag can optionally take nested block content. However, in this example this is not necessary, and therefore we "close" the tag with a forward slash `/` much like with xml tags. Without explicitly closing the tag the template parser would expect a `{% /TodoItem %}` closing tag.


### `TodoItem` Component

Next, we create a `TodoItem` component.

``` python
class TodoItem(Component):
    title = public("")
    done = public(False)

    def load(self, todo, *args, **kwargs):
        self.todo = todo
        self.title = todo.title
        self.done = todo.done
```
 As we have previously seen, there are public attributes to hold the `title` and `done` status of the item. The load method takes a `ToDo` model instance (passed to it in the template above), then saves it as a private attribute on the component, and finally sets the `title` and `done` public attributes.



``` python
    @public.watch('title', 'done').debounce(200)
    def save(self, value, old_value, attr):
        self.todo.title = self.title
        self.todo.done = self.done
        self.todo.save()
```

The public `save` method is set to `watch` the `title` and `done` public attributes with a `debounce` of 200ms. This instructs Alpine.js to call the server side `save` method automatically whenever the `title` and `done` attributes change. The `debounce(200)` ensures that the save method isn't called on every keystroke whilst typing.

Next, there is a public `delete_item` method, which is simply calling the delete method on the Django model instance attached to the component.

``` python
    @public(update=False)
    def delete_item(self):
        self.todo.delete()
        self.client._removeComponent()
```

 However, there are a couple of other things happening in there too:

- We have set `update=False` when creating the public method. By default, public methods will re-render the component and send the new html to the browser. However, in this instance we don't need to do this, and have therefore disabled it.
- We call `self.client._removeComponent()`
- `self.client` is a "callback queue" that allows you to schedule callbacks of client JavaScript methods for when the client receives a response from the method. You can call any of your custom JavaScript methods via this API. The `self.client._removeComponent()` is a method available on all components, instructing the client to remove the component from the DOM - this is ideal for when deleting items.


This component template uses some concepts we saw on the previous component, attaching public attributes to inputs with the Alpine.js `x-model` directive and event listeners with the `@event` directives. In this case we are binding `@keydown.backspace` and `@keyup.backspace` on the text input to custom JavaScript methods which we are going to define later on.

We have used the Alpine.js class binding `:class` to set the CSS class depending on the `done` attribute.

``` python
    template: django_html = """
    <div class="list-group-item d-flex gap-1 p-1">
        <label class="align-middle px-2 d-flex">
            <input class="form-check-input m-0 align-self-center" type="checkbox"
                x-model="done">
        </label>
        <input 
            type="text" 
            class="form-control border-0 p-0 m-0"
            :class="{'text-muted': done, 'todo-strike': done}"
            x-model="title"
            maxlength="80"
            @keydown.backspace="inputDeleteDown()"
            @keyup.backspace="inputDeleteUp()"
        >
        <button @click="delete_item()" class="btn btn-sm">
            <i class="fa-solid fa-trash"></i>
        </button>
    </div>
    """
```

This component introduces the concept of client side JavaScript methods; these are created on the `script` attribute as a multiline Python string. We are again using the `javascript` type annotation to indicate to our editor which syntax highlighting to use.

The script should use `export default` to expose an object that is used to construct the Alpine.js component - this is mixed in with your component's public attributes/methods, along with some additional Tetra methods to `Alpine.data()`. You can read more about [Alpine.data](https://alpinejs.dev/globals/alpine-data).

If you are using other JavaScript libraries it is possible to `import` them here.

Your JavaScript is "built" using [esbuild](https://esbuild.github.io), packaging all components within one "library" into a single package. Sourcemaps are created, mapping back to your original Python files to aid in debugging.

Note that our `inputDeleteUp` method below calls `this.delete_item()` -  this is a public method implemented in Python above. Convention is to use "snake_case" for Python methods and attributes, and "camelCase" for JavaScript methods and attributes, for ease of identification.

``` python
    script: javascript = """
    export default {
        lastTitleValue: "",
        inputDeleteDown() {
            this.lastTitleValue = this.title;
        },
        inputDeleteUp() {
            if (this.title === "" && this.lastTitleValue === "") {
                // If the input was all ready empty when we pressed backspace then
                // delete the to do item.
                this.delete_item()
            }
        }
    }
    """
```

Next, we define some CSS styles for the component as the multiline Python string attribute `styles`. This again uses a `css` type annotation for syntax highlighting. Styles for all components in a library are bundled together using esbuild, and again source maps are generated, mapping back to the original Python source code.

``` python
    style: css = """
    .todo-strike {
        text-decoration: line-through;
    }
    """
```

### Including the "todo" list in a page

Finally, we include our `TodoList` component into a pages template using the component tag.
As we are doing this outside of a Tetra component we need to explicitly load the Tetra template tags with `{% load tetra %}`.

``` django
{# index.html #}
<h4>Your todo list:</h4>
{% TodoList / %}
```

 To get started, follow the [install instructions](install.md).