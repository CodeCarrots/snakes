from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.shortcuts import redirect
import snakes_app.urls


def redirect_snake(request, key):
    return redirect('/snakes_app/snake/%s/' % (key))


def redirect_root(request):
    return redirect('/snakes_app/')


urlpatterns = patterns('',
    url(r'^$', redirect_root),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^snake/(?P<key>[a-zA-Z0-9]+)/$', redirect_snake),
    url(r'^snakes_app/', include(snakes_app.urls))
)
