from django.conf.urls import include, re_path

from snakes_app import views


urlpatterns = [
    # Examples:
    re_path(r'^$', views.board, name='board'),
    re_path(r'^snake/(?P<key>[a-zA-Z0-9]+)/$', views.key_board, name='board'),
    re_path(r'^errors/(?P<key>[a-zA-Z0-9]+)/$', views.error_log, name='error_log'),
    re_path(r'^board/', views.check_board, name='board-json'),
    re_path(r'^leaderboard/', views.leaderboard, name='leaderboard-json'),
    re_path(r'^reload/', views.reload_code, name='reload'),
]
