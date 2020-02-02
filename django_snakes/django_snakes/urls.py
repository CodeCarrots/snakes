from django.conf.urls import include, re_path
from django.shortcuts import redirect
import snakes_app.urls


def redirect_snake(request, key):
    return redirect('/snakes_app/snake/%s/' % (key))


def redirect_root(request):
    return redirect('/snakes_app/')


urlpatterns = [
    re_path(r'^$', redirect_root),
    re_path(r'^snake/(?P<key>[a-zA-Z0-9]+)/$', redirect_snake),
    re_path(r'^snakes_app/', include(snakes_app.urls))
]
