from sourcetypes import javascript, css, django_html
from tetra import Component, public, Library
import itertools
from .models import ToDo
from .movies import movies

default = Library()


@default.register
class ToDoList(Component):
    title = public("")

    def load(self):
        self.todos = ToDo.objects.filter(session_key=self.request.session.session_key)

    @public
    def add_todo(self, title):
        todo = ToDo(
            title=title,
            session_key=self.request.session.session_key,
        )
        todo.save()
        self.title = ""

    template: django_html = """
    <div>
        <div class="input-group mb-2">
            <input type="text" x-model="title" class="form-control" 
                placeholder="New task..." @keyup.enter="add_todo(title)">
            <button class="btn btn-primary" @click="add_todo(title)">Add</button>
        </div>
        <div class="list-group">
            {% for todo in todos %}
                {% @ to_do_item todo=todo key=todo.id / %}
            {% endfor %}
        </div>
    </div>
    """


@default.register
class ToDoItem(Component):
    title = public("")
    done = public(False)

    def load(self, todo):
        self.todo = todo
        self.title = todo.title
        self.done = todo.done

    @public.watch("title", "done").debounce(200)
    def save(self, value, old_value, attr):
        self.todo.title = self.title
        self.todo.done = self.done
        self.todo.save()

    @public(update=False)
    def delete_item(self):
        self.todo.delete()
        self.client._removeComponent()

    template: django_html = """
    <div class="list-group-item d-flex gap-1 p-1" {% ... attrs %}>
        <label class="align-middle px-2 d-flex">
            <input class="form-check-input m-0 align-self-center" type="checkbox"
                x-model="done">
        </label>
        <input 
            type="text" 
            class="form-control border-0 p-0 m-0"
            :class="{'text-muted': done, 'todo-strike': done}"
            x-model="title"
            maxlength="80"
            @keydown.backspace="inputDeleteDown()"
            @keyup.backspace="inputDeleteUp()"
        >
        <button @click="delete_item()" class="btn btn-sm">
            <i class="fa-solid fa-trash"></i>
        </button>
    </div>
    """

    script: javascript = """
    export default {
        lastTitleValue: "",
        inputDeleteDown() {
            this.lastTitleValue = this.title;
        },
        inputDeleteUp() {
            if (this.title === "" && this.lastTitleValue === "") {
                this.delete_item()
            }
        }
    }
    """

    style: css = """
    .todo-strike {
        text-decoration: line-through;
    }
    """


@default.register
class Counter(Component):
    count = 0
    current_sum = 0

    def load(self, current_sum=None):
        if current_sum is not None:
            self.current_sum = current_sum

    @public
    def increment(self):
        self.count += 1

    def sum(self):
        return self.count + self.current_sum

    template: django_html = """
    <div class="border rounded p-3">
        <p>
            Count: <b>{{ count }}</b>,
            Sum: <b>{{ sum }}</b>
            <button class="btn btn-sm btn-primary" @click="increment()">Increment</button>
        </p>
        <div>
            {% block default %}{% endblock %}
        </div>
    </div>
    """


@default.register
class reactive_search(Component):
    query = public("")
    results = []

    @public.watch("query").throttle(200, leading=False, trailing=True)
    def watch_query(self, value, old_value, attr):
        if self.query:
            self.results = itertools.islice(
                (movie for movie in movies if self.query.lower() in movie.lower()), 20
            )
        else:
            self.results = []

    template: django_html = """
    <div>
        <p>
            <input class="form-control" placeholder="Search for an 80s movie..."
            type="text" x-model="query">
        </p>
        <ul>
        {% for result in results %}
            <li>{{ result }}</li>
        {% endfor %}
        </ul>
    </div>
    """
