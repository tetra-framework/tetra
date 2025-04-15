---
title: Component life cycle
---

# Attribute data life cycle

The data attributes of a component exist within a specific lifecycle. The component, when constructed or resumed sets its atributes in a certain order (see below). In each step, the already existing attribute data are overridden.

## 1. Attribute assignment

```python
class Person(Component):
    name:str = "John Doe"
    age:int = None

    ...
```

When Attributes are set directly in the class, they are used as default values, as in any other python class too. Even if no `load()` method is present, the component can use this values.

## 2. Resumed data from encrypted state

If the component is resumed from a previous state, the encrypted state data is decrypted, and all component attributes are set from the previous state.
This is omitted if the component is initialized the first time, as there is no encrypted previous state yet.

## 3. The `load()` method

Next, the component's `load()` method is called. Any data assignment to the attributes overrides the previous values.

```python
class Person(Component):
    name:str = "John Doe"
    age:int = None

    def load(self, pk:int, *args, **kwargs):
        person = Person.objects.get(pk=pk)
        self.name = person.name
        self.age = person.age
```

Attributes that set in the `load()` method are **not** saved with the state, as the values are overwritten in the subsequent step. This seems to be extraneous, but in fact makes sure that the component attributes gets a consistent initialization.


## 4. The client data

The final step involves updating attributes using *data* passed from the client-side to the server via component methods. Note that this is not the same as the *state*:

 * The **state** represents the "frozen data" sent to the client during the last render, essentially what the client received initially. 
 * The **data** refers to dynamic values, such as a component input tag's value, which may have changed during the last interaction cycle.


# Events on the client side

On the client, there are certain javascript events fired when certain things happen. You can react on that using Alpine's `x-on` or by using custom Javascript code.

All events have the actual component as `component` payload attached.

## Events

### `tetra:afterRequest`

This event fires after a component method has completed — whether the request was successful (even if the response includes an HTTP error like 404) or if a network error occurred. It can be used alongside `tetra:beforeRequest` to implement custom behavior around the full request lifecycle, such as showing or hiding a loading indicator.


### `tetra:beforeRequest`

This event is triggered before a component method is called.


### `tetra:componentUpdated`
This event is fired after a component has called a public method and the new HTML is completely morphed into the DOM.
It is also fired after a component has been replaced.

```html
<div @tetra:componentUpdated="message='component was updated'">
  <span x-text="message">Original text</span>
</div>
```

### `tetra:componentDataUpdated`

Same goes for data updates - the event is fired after a data update without HTML changes was finished.

### `tetra:componentBeforeRemove`

Right before a component is removed using `self.client._removeComponent()` this event is triggered.

### `tetra:childComponentDestroy`

Called before a child component is going to be destroyed.

#### Details

* `component` - The component that is destroyed

# Sequence diagram

What happens when a public method is called? This sequence diagram shows everything.
```mermaid
sequenceDiagram
  box Client
  participant Client  
  end

  box Server
  participant Server  
  participant component_method  
  participant Component  
  participant TetraJSONEncoder  
  participant TetraJSONDecoder  
  participant decode_component  
  participant StateUnpickler 
  end

  Client->> Server: POST request to /component_method/
  Server ->> component_method: Call component_method() view
  component_method ->> component_method: Set PersistentTemporaryFileUploadHandler
  component_method ->> component_method: Validate request method (==POST?)
  component_method ->> component_method: Retrieve Component class from Library list
  component_method ->> component_method: Validate method name is public
  component_method ->> TetraJSONDecoder: Decode request.POST data (from_json)
  TetraJSONDecoder -->> component_method: Return decoded data
  component_method ->> component_method: Add Component class to set of used components in this request
  component_method ->> Component: Request new component instance (using Component.from_state)
  Component ->> Component: Validate ComponentState data structure

  Component ->> decode_component: decode_component(ComponentState["state"], request)
  decode_component ->> decode_component: get fernet for request
  decode_component ->> decode_component: decrypt encoded state_token using fernet
  decode_component ->> decode_component: decompress decrypted data with gzip
  decode_component ->> StateUnpickler: unpickle component data state
  StateUnpickler -->> decode_component: component
  decode_component -->> Component: component

  Component ->> Component: Set component request, key, attrs, context, blocks
  Component ->> Component: recall load() with initial params
  Component ->> Component: set component attributes from client data
  Component ->> Component: client data contains a Model PK? -> replace it with Model instance from DB
  Component ->> Component: hook: recalculate_attrs(component_method_finished=False)
  Component -->> component_method: Return initialized component instance


  component_method ->> component_method: Attach uploaded files (from request.FILES) to component
  component_method ->> Component: Call Component's _call_public_method
  Component ->> Component: Execute public method

  Component ->> TetraJSONEncoder: Encode result data to JSON
  TetraJSONEncoder -->> Component: Return JSON-encoded data

  Note over Component: JSON response
  Component -->> component_method: Return encoded result
  component_method -->> Server: Return JsonResponse
  Server -->>Client: Send response


```
