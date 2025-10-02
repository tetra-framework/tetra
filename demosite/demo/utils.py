from django.utils.translation import gettext_lazy as _
from .models import ToDo


to_do_defaults = [
    (True, _("Discover Tetra")),
    (False, _("Install and explore Tetra")),
    (False, _("Decide to build your next startup using Tetra")),
    (False, _("Become a billionaire")),
    (False, _("Start a rocket company")),
    (False, _("Populate Pluto, it's a much cooler planet than Mars")),
]


def prepopulate_session_to_do(request) -> None:
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    if ToDo.objects.filter(session_key=session_key).count() == 0:
        todos = [
            ToDo(done=d, title=_(str(t)), session_key=session_key)
            for d, t in to_do_defaults
        ]
        ToDo.objects.bulk_create(todos)
