from sourcetypes import django_html

from tetra import BasicComponent


class Col(BasicComponent):
    def load(self, title="", *args, **kwargs):
        self.title = title

    # language=html
    template: django_html = """
    <div class="col">
      <h6 class="fw-bold mb-0">
      {% block title %}{% if title %}{{ title }}{% endif %}{% endblock %}
      </h6>
      <p>{% block default %}{% endblock %}</p>
    </div>
    """
