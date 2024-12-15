---
title: Delete Row
---

# Delete Row

Here's an example component demonstrating how to create a delete button that removes a table row when clicked.

{% md_include_source "demo/components/examples/delete_row_table/__init__.py" %}
{% md_include_source "demo/components/examples/delete_row_table/delete_row_table.html" %}

So far for the table component. The rows are components themselves. Each row is responsible for its own deletion. So there is no `delete_item(some_id)` necessary, as the component already knows its id since it internally saves its state. `delete_item()` is sufficient within the component's template code.

{% md_include_source "demo/components/examples/delete_row/__init__.py" %}

{% md_include_source "demo/components/examples/delete_row/delete_row.html" %}
