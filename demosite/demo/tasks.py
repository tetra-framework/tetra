import asyncio
import random

from tetra.dispatcher import ComponentDispatcher


async def send_breaking_news_to_channel():
    from demo.models import BreakingNews
    while True:
        count = await BreakingNews.objects.acount()
        offset = random.randint(0, count - 1)
        news = await BreakingNews.objects.all()[offset : offset + 1].aget()
        await ComponentDispatcher.update_data(
            "notifications.news.headline",
            data={
                "headline": news.title,
            },
        )
        await asyncio.sleep(10)
