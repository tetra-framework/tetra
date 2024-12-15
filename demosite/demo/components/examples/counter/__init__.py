from tetra import Component, public


class Counter(Component):
    count: int = 0

    @public
    def increment(self):
        self.count += 1
