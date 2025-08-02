from tetra import Component, public


class Counter(Component):
    count = 0
    current_sum = 0

    def load(self, current_sum=None, *args, **kwargs):
        if current_sum is not None:
            self.current_sum = current_sum

    @public
    def increment(self):
        self.count += 1

    @public
    def decrement(self):
        self.count -= 1

    def sum(self):
        return self.count + self.current_sum
