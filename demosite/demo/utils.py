from .models import ToDo


to_do_defaults = [
    (True, "Discover Tetra"),
    (False, "Install and explore Tetra"),
    (False, "Decide to build your next startup using Tetra"),
    (False, "Become a billionaire"),
    (False, "Start a rocket company"),
    (False, "Populate Pluto, it's a much cooler planet than Mars"),
]


def prepopulate_session_to_do(request):
    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key
    if ToDo.objects.filter(session_key=session_key).count() == 0:
        todos = [
            ToDo(done=d, title=t, session_key=session_key) for d, t in to_do_defaults
        ]
        ToDo.objects.bulk_create(todos)
