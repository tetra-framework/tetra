import itertools
from tetra import Component, public
from demo.movies import movies


class ReactiveSearch(Component):
    query = public("")
    results = []

    @public.watch("query")
    @public.throttle(200, leading=False, trailing=True)
    def watch_query(self, value, old_value, attr):
        if self.query:
            self.results = itertools.islice(
                (movie for movie in movies if self.query.lower() in movie.lower()),
                20,
            )
        else:
            self.results = []
