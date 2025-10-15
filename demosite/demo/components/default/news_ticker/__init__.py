import random
from demo.models import BreakingNews
from tetra import public, ReactiveComponent


class NewsTicker(ReactiveComponent):
    headline: str = public("")
    # could be a fixed subscription too:
    # subscribe = ["notifications.news.headline"]

    def load(self, *args, **kwargs) -> None:
        # Fetch the latest news headline from database
        self.breaking_news = BreakingNews.objects.all()
        # get random item from BreakingNews
        self.headline = random.choice(self.breaking_news).title
