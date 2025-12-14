class CallbackPath:
    def __init__(self, root, path=("",)):
        self.root = root
        self.path = path

    def __getattr__(self, name):
        return CallbackPath(self.root, self.path + (name,))

    def __getitem__(self, name):
        return self.__getattr__(name)

    def __call__(self, *args):
        self.root.callbacks.append(
            {
                "callback": self.path,
                "args": args,
            }
        )


class CallbackList:
    def __init__(self):
        self.callbacks = []

    def __getattr__(self, name):
        return CallbackPath(self, (name,))

    def __getitem__(self, name):
        return self.__getattr__(name)

    def serialize(self):
        return self.callbacks
