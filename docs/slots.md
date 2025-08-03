---
title: Template Slots
---


# Template Slots

Slots* are to component templates basically what *blocks* are to Django templates. You can define  one or more slots in your component's template, and override their content when rendering the component in your Django template.

Define a slot in your "News" component's template by using `{% slot <name> %}`:

```django
<div class="news-card" {% ... attrs %}>
  <h3>News!<h3>
  {% slot content %}
  {% endslot %}
</div>
```

You can use this component in your template as usual, and fill the slot with your content.

``` django
{% News %}
  {% slot content %}Lorem ipsum dolor{% endslot %}
{% /News %}
```


## The `default` slot

If you pass content to a component without a top-level slot it infers that you are targeting the `default` slot, e.g. in a Bootstrap "Card" component:

```django
<div class="card" {% ... attrs %}>
  <div class="card-body">
    <p class="card-text">
      {% slot default %}
      {% endslot %}
    </p>
  </div>
</div>
```
Usage:
``` django
{% Card %}
  Some content
{% /Card %}
```

Is the equivalent of:

``` django
{% Card %}
  {% slot default %}
    Some content
  {% endslot %}
{% /Card %}
```

## Multiple slots

You can pass as many slots to a component as you like:

``` django
<div class="card" {% ... attrs %}>
  <h5 class="card-title">
    {% slot title %}
    {% endslot %}
  </h5>
  <div class="card-body">
    <p class="card-text">
      {% slot default %}
      {% endslot %}
    </p>
  </div>
</div>
```

```django
{% Card %}
  {% slot title %}News{% endslot %}
  {% slot default %}
    {{ news_entry.content|safe }}
  {% endslot %}
{% /Card %}
```

By default, slots are scoped within a component, so that you can use components multiple times on a page and not have slot names conflict with each other.

It is, however, possible to explicitly **expose** a slot to the wider template so that it can be overridden with the `expose` flag:

``` django
{% MyComponent %}
  {% slot title expose %}
    Some content
  {% endslot %}
{% /MyComponent %}
```

You can also specify under what name a slot should be exposed with `expose as [name]`:

``` django
{% MyComponent %}
  {% slot title expose as header_title %}
    Some content
  {% endslot %}
{% /MyComponent %}
```

See [component templates](components.md#templates) for details of how the component handles slots in its templates.
