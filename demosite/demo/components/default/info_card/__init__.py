from sourcetypes import django_html
from django.utils.translation import gettext_lazy as _

from tetra import Component, public


class InfoCard(Component):
    title: str = _("I'm so excited!")
    content: str = _("We got news for you.")
    name: str = public("")

    @public
    def close(self):
        self.client._removeComponent()

    @public
    def done(self):
        print("User clicked on OK, username:", self.name)
        self.content = _("Hi {name}! No further news.").format(name=self.name)

    # language=html
    template: django_html = """
    {% load i18n %}
    <div class="card text-white bg-secondary mb-3" style="max-width: 18rem;">
      <div class="card-header d-flex justify-content-between">
        <h3>{% translate "Information" %}</h3>
        <button class="btn btn-sm btn-warning" @click="_removeComponent(
        )"><i class="fa fa-x"></i></button>
      </div>
      
      <div class="card-body">
        <h5 class="card-title">{{ title }}</h5>
        <p class="card-text">
          {{ content }}
        </p>
        <p x-show="!name">
          {% translate "Enter your name below!" %}
        </p>
        <p x-show="name">
            {% translate "Thanks," %} {% livevar name %}
        </p>
        <div class="input-group mb-3">

          <input 
            type="text" 
            class="form-control" 
            placeholder="{% translate 'Your name' %}"
            @keyup.enter="done()"
            x-model="name">
        </div>
        <button 
            class="btn btn-primary" 
            @click="done()" 
            :disabled="name == ''">
            {% translate "Ok" %}
        </button>
      </div>
      
    </div>
    """
