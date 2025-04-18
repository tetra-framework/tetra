---
title: File handling in Tetra
---

# File handling in Tetra

## File uploads

When using HTML file input tags, Tetra's [FormComponent](form-components.md) takes care of the uploading process. While in normal HTML `<form>` elements a file upload can only happen with special precautions (form enctype=multipart/form-data; page is never reloaded using validation with GET because the browser deletes the file then), `FormComponent` takes care of the uploading process within a component automatically:

* Whenever the first `POST` request is fired, the file is sent to the server. You don't have to create a `form enctype=multipart/form-data` etc., Tetra does that automatically.
* The file is then saved temporarily on the server, until the `submit()` method is called finally
* Now the file is copied to its final destination and attached to the form's field.

So there's not anything to mention. Just use a FileField in your `FormComponent`

```python
class PersonForm(Form):
    name = forms.CharField()
    attachment = forms.FileField(upload_to="attachments/")

class PersonComponent(FormComponent):
    form_class = PersonForm
```

## File downloads

You can place any link to a staticfile as `<a href="...>` tag in a component. This is like in normal HTML code, there is nothing special in it.

But what you may need in special cases is a more dynamic behavior of links:

* "hiding" the link to a file from the public
* creating dynamic content during the click
* creating in-memory data (as file) that must not be saved on the server due to security concerns (e.g. on-the-fly created credentials)

All easy with Tetra:

When a component method is called, the [return value is sent](components.md#return-values-of-public-methods) to the JavaScript caller. Tetra is smart enough to detect if a return value is a FileResponse, and makes the browser download that file instead of updating the DOM:

```python
class Person(Component):
    first_name:str = public("")
    last_name:str = public("")

    template = """..."""

    @public
    def download(self) -> FileResponse|None:
        if self.request.user.is_authenticated:
            pdf_file = generate_pdf_from_some_template(
                "/path/to/template.pdf", {
                    "first_name": self.first_name,
                    "last_name": self.last_name,
                    "password": some_random_generated_password(),
                }
            )
            return FileResponse(content_type="application/pdf", filename="credentials.pdf")
        
        # if user is not authenticated, the normal Tetra response is executed, 
        # so the component just updates itself.
```

You can also return a `FileResponse(open(/path/to/file.dat), ...)` to offer a downloadable file that has no publicly available URL.
Just make sure that content_type and filename is provided