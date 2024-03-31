---
title: Alpine.js Magic
---

# Alpine.js Magic: `$static`

The `$static(path)` Alpine.js magic is the client side equivalent of the [Django `static` template tag](https://docs.djangoproject.com/en/4.2/ref/templates/builtins/#static). It takes a path in string form relative to your static root and returns the correct path to the file, whether it is on the same host, or on a completely different domain.

