from time import sleep
from tetra import Component, public


class LoadingIndicatorDemo(Component):

    @public
    def long_lasting_process(self):
        sleep(2)
