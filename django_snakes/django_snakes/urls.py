from django.conf.urls import patterns, include, url
from django.contrib import admin

import snakes_app.urls


urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'snakes_app/', include(snakes_app.urls))
)
