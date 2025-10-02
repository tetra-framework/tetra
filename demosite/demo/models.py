from django.db import models
from django.utils.translation import gettext_lazy as _


class ToDo(models.Model):
    class Meta:
        verbose_name = _("ToDo")
        verbose_name_plural = _("ToDos")

    session_key = models.CharField(max_length=40, db_index=True)
    title = models.CharField(max_length=80)
    done = models.BooleanField(default=False)
    added = models.DateTimeField(auto_now_add=True, db_index=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class BreakingNews(models.Model):

    class Meta:
        verbose_name_plural = _("Breaking news")

    title = models.CharField(max_length=100)

    def __str__(self):
        return self.title
