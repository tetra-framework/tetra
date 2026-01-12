Title: Messaging integration

# Message framework integration

## Django Messages
Tetra integrates deeply Django's messaging framework. A traditional Django approach is to fetch all messages into the template and display them.

In a component based layout as Tetra describes, where individual components independently make AJAX calls and update themselves, it is not as easy. You may have one component that gets the messages, but it is not notified about that when another component calls a method. Then, all messages would be stuck in the wrong response/component, so this doesn't help. Even when notifying the "messages" component so that it could get the new messages, would help, it would even make things worse, as there would be race conditions when 2 components update, and the messages component updates itself too twice, overwriting the first message with the proceeding one.

## Tetra Messages — brought by events
So, the messaging must be kept independently on the client. Tetra tries to solve this by providing new messages, whenever they occur, with any call of any component, through the middleware. `TetraMiddleware` and Tetra's client JavaScript part process all messages and convert them into JavaScript objects that are then sent individually via a fired event: `tetra:new-message`.

You can react on it in any component, using client side/Alpine.js or server side code:

```django
<div x-data="{bell: false}" @tetra:new-message="bell=true">
  <i class="bi bi-bell" x-show="bell"></i>
 </div>
```
This shows a Bootstrap bell icon whenever a new message has arrived, instantly. You can also call a function, the message itself is added as the "details" attribute of the event.

```django
<div @tetra:new-message="show_message($event.details)"></div>
```

Since Tetra provides a [@public.listen](components.md#listen) modifieruv build, you can even react on the server on that:
```python
from django.contrib.messages import Message

class MyComponent(Component):
    
    @public.listen("tetra:new-message")
    def message_added(self, message:Message):
        ...
```
!!! note
    This makes only sense in certain scenarios, as the roundtrips Message generation -> Middleware -> Client event emitting -> AJAX call of backend method is a bit much for just reacting on a message.

Tetra takes care of the serialization/transition from a Django `Message` to a full Javascript object with all necessary data available, including a boolean "dismissible" attribute.

### Message Attributes

Django knows only three attributes: `message:str`, `level:int` and `extra_tags:str`, and dynamically builds the tags and level_tags as properties from them.

```javascript
// Message anatomy
{
    message: "Successfully saved File",
    uid: "5d68f405-8427-4e04-80b7-0996bf5e3629",
    level: 25,
    level_tag: "bg-success-lt",
    tags: "success dismissible",
    extra_tags: "dismissible",
    dismissible: true
}
```

#### The `.uid` attribute

In Django, there is no UID in messages. You could change your Message/Storage type by using `settings.MESSAGE_STORAGE`, but this is not necessary. We need the UID of each message only on the client.

So each message gets an UID during the middleware transition, so it can be displayed and deleted individually.  Just make sure to include the MessageMiddleware, and TetraMiddleware. The messages are transported via a special `T-Messages` response header.

#### The `.dismissible` attribute: a special case

There are cases where messages should be "sticky". In this case, you can add the extra_tag "dismissible" to the message, and Tetra will treat it specially:

```python
messages.warning("You did something nasty.", extra_tags="dismissible")
```

In this case, the message will get a boolean attribute `.dismissible` on the client, so you could filter them out easier.

```javascript
export default {
    message_arrived(message) {
        if(message.dismissible) {
            console.log("To whom it may concern: A sticky message waits to be clicked aẃay by the user.")
        }
    }
}
```
