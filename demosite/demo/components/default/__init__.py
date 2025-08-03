from sourcetypes import django_html

from tetra import BasicComponent


class Col(BasicComponent):
    def load(self, title="", *args, **kwargs):
        self.title = title

    # language=html
    template: django_html = """
    <div class="col">
      <h6 class="fw-bold mb-0">
      {% slot title %}{% if title %}{{ title }}{% endif %}{% endslot %}
      </h6>
      <p>{% slot default %}{% endslot %}</p>
    </div>
    """
