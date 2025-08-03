from sourcetypes import django_html

from tetra import Component, public


class InfoCard(Component):
    title: str = "I'm so excited!"
    content: str = "We got news for you."
    name: str = public("")

    @public
    def close(self):
        self.client._removeComponent()

    @public
    def done(self):
        print("User clicked on OK, username:", self.name)
        self.content = f"Hi { self.name }! No further news."

    template: django_html = """
    <div class="card text-white bg-secondary mb-3" style="max-width: 18rem;">
      <div class="card-header d-flex justify-content-between">
        <h3>Information</h3>
        <button class="btn btn-sm btn-warning" @click="_removeComponent(
        )"><i class="fa fa-x"></i></button>
      </div>
      
      <div class="card-body">
        <h5 class="card-title">{{ title }}</h5>
        <p class="card-text">
          {{ content }}
        </p>
        <p x-show="!name">
          Enter your name below!
        </p>
        <p x-show="name">
            Thanks, {% livevar name %}
        </p>
        <div class="input-group mb-3">

          <input 
            type="text" 
            class="form-control" 
            placeholder="Your name" 
            @keyup.enter="done()"
            x-model="name">
        </div>
        <button 
            class="btn btn-primary" 
            @click="done()" 
            :disabled="name == ''">
            Ok
        </button>
      </div>
      
    </div>
    """
