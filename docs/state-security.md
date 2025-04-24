---
title: Saved Server State and Security
---

# Saved Server State and Security

When a component is rendered, as well as making its public state available as JSON to the client, it saves its server state so that it can be resumed later. This is done using the builtin Python Pickle toolkit. The "Pickled" state is then encrypted using 128-bit AES and authenticated with HMAC via [Fernet](https://cryptography.io/en/latest/fernet/) using a key derived from your Django settings `SECRET_KEY` and the user's session id using [HKDF](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#hkdf).

This state is then sent to the client and resubmitted back to the server for unpickling on further requests via public methods. Each time the state changes on the server a new pickled state is created and sent to the client.

By using Pickle for the serialisation of the server state we are able to support a very broad range of object types, effectively almost anything.

It is essential that the Django `SECRET_KEY` is kept secure. It should never be checked into source controls, and ideally be stored securely by a secrets management system.

As this encrypted server state was generated after the component had been passed its arguments, and after any view based authentication, it holds onto that authentication when resumed later. It is, in effect, an authentication token allowing the user to continue from that state at a later point in time. It is also possible to do further authentication within the `load()` method, or any other public method.

## State optimizations

A number of optimizations have been made to ensure that the Pickled state is efficient and doesn't become stale. These include:

- Models are saved as just a reference to the model type and the primary key. They are then retrieved from the database when unpickling. This ensures that they always present the latest data to your public methods.

- QuerySets are saved in raw query form, not including any of the results. After unpickling, they are then lazily run to retrieve results from the database when required.

- Template Blocks passed to a component are saved as just a reference to where they originated. This is almost always possible. It includes blocks defined within a component's template, or blocks in templates loaded using a Django built-in template loader.

- When a component runs its `load` method, it tracks what properties are set. These are then excluded from the data when pickling. The `load` method is re-run after unpickling using the same arguments it was originally passed, or updated arguments if it is being resumed as a child component.