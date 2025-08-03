---
title: Introduction
---

# Introduction

![Logo](img/logo.svg)

Tetra is a full stack component framework for [Django](https://docs.djangoproject.com) using [Alpine.js](https://alpinejs.dev), bridging the gap between your server logic and front end presentation. It is built on a couple of key principles:

  - Proximity of related concerns is as important as separation of concerns. Whilst it is important to keep your backend logic, front end JavaScript, HTML, and styles separate, it is also incredibly useful to have related code in close proximity.

    Front end toolkits such as Vue.js, with its single file components and newer "utility class" based CSS frameworks such as Tailwind, have shown that keeping related aspects of a component in the same file helps to reduce code rot, and to improve the speed at which developers gain an understanding of the component.

  - Building APIs as a bridge between your server side and front end code adds complexity and developer overhead - Tetra allows for much less of this. Server side rendering allows you to move more quickly without having to create further layers and abstractions.
  
    Frameworks such as Laravel Livewire and Phoenix Liveview, which heavily inspired Tetra, have shown that server side rendering with smart "morphing" of the DOM in the browser is an incredibly efficient way to build websites and apps.

Tetra components encapsulate all aspects of their functionality into one definition in a single file/directory. The server side Python/Django code, HTML template, front end JavaScript (using Alpine.js), and CSS styles are side by side.

Furthermore, components can expose attributes and methods as *public*, making them available to the front end Alpine.js JavaScript code.

[Alpine.js](https://alpinejs.dev) is a lightweight front end toolkit that exposes a reactive state to your html, providing a way to build front end components. If you haven't previously used Alpine.js, now is the time to go and follow their [brief tutorial](https://alpinejs.dev/start-here ). 

*Tetra takes the four "faces" of a component and combines them into one composable object.*


## Walkthrough of a simple "To Do App"

To introduce the main aspects of Tetra we will walk through the code implementing the [To Do App demo](https://tetraframework.com/#examples) on the homepage.

Proceed to our [tutorial](tutorial.md).


!!! note
    Tetra is still early in its development, and we can make no promises about API stability at this stage.

    The intention is to stabilise the API prior to a v1.0 release, as well as implementing additional functionality step by step.