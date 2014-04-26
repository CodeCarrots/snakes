from django.conf.urls import patterns, include, url


urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'snakes_app.views.board', name='board'),
    url(r'^snake/(?P<key>[a-zA-Z0-9]+)/$', 'snakes_app.views.key_board', name='board'),
    url(r'^errors/(?P<key>[a-zA-Z0-9]+)/$', 'snakes_app.views.error_log', name='error_log'),
    url(r'^board/', 'snakes_app.views.check_board', name='board-json'),
    url(r'^leaderboard/', 'snakes_app.views.leaderboard', name='leaderboard-json'),
    url(r'^reload/', 'snakes_app.views.reload_code', name='reload'),
)