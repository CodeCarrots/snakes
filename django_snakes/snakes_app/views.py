from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect

import json
from snakes.db import get_db
from snakes.example import get_example


r = get_db()


def json_response(view):
    def json_view(request, *args, **kwargs):
        response = view(request, *args, **kwargs)
        return HttpResponse(json.dumps(response), content_type="application/json")
    return json_view


def board(request):
    snake_name = 'Annonymous'
    snake_color = '#fff'
    snake_err = ''

    return render(
        request,
        'snakes_app/board.html',
        {
            'board': r.get('board'),
            'key': None
        })


def key_board(request, key):
    snake_name = r.get('snake:%s:name' % key)
    snake_color = '#fff'
    snake_err = ''
    if snake_name is None:
        return redirect('/snakes_app/')
    else:
        invalid_key = False
        snake_name = snake_name.decode('utf-8')
        snake_code = r.get('snake:%s:code' % key).decode('utf-8')
        # snake_code = (r.get('snake:%s:code' % key) or script).decode('utf-8')
        snake_color = (r.get('snake:%s:color' % key) or '#fff').decode('utf-8')
        snake_err = (r.get('snake:%s:err' % key) or '').decode('utf-8')

    return render(
        request,
        'snakes_app/board.html',
        {
            'board': r.get('board'),
            'key': key,
            'name': snake_name,
            'code': snake_code,
            'color': snake_color,
            'err': snake_err,
            'invalid_key': invalid_key
        })


@json_response
def check_board(request):
    snakes = r.get('snakes')
    key = request.GET.get('KEY')
    snakes = json.loads(snakes.decode('utf-8'))
    if snakes is None:
        return {'snakes': []}

    if key is None:
        return snakes

    snake_err = (r.get('snake:%s:err' % key) or '').decode('utf-8')
    snaker_err_lines = snake_err.split("\n")[-20:]

    for snake in snakes['snakes']:
        snake['current'] = snake['key'] == key
        del snake['key']

    snakes['err'] = "\n".join(snaker_err_lines)
    return snakes


def get_snake_name(key):
    name = r.get('snake:%s:name' % key)
    if name is not None:
        return name.decode('utf-8')
    else:
        return u'Annonymous'


def get_snake_color(key):
    name = r.get('snake:%s:color' % key)
    return 'black' if name is None else name


def leaderboard(request):
    members = [
        {
           'name': get_snake_name(s[0]),
           'score': int(s[1]),
           'color': get_snake_color(s[0])
        }
        for s in r.zrevrange('leaderboard', 0, -1, withscores=True)]
    return render(request, 'snakes_app/leaderboard.html', dict(members=members))


def error_log(request, key):
    snake_errors = r.get('snake:%s:err' % (key,))
    return HttpResponse(snake_errors)


def reload_code(request):
    if (';' in request.POST['slave_name']
        or len(request.POST['slave_id']) == 0
        or len(request.POST['slave_name']) == 0
        or len(request.POST['slave_code']) == 0):
        return redirect(reverse('board'))

    command = json.dumps((
        'reload_slave',
        request.POST['slave_id'],
        request.POST['slave_name'],
        request.POST['slave_code']
    ))
    r.rpush('commands', command.encode('utf-8'))
    r.set('snake:%s:name' % request.POST['slave_id'].encode('utf-8'),
          request.POST['slave_name'].encode('utf-8'))
    r.set('snake:%s:code' % request.POST['slave_id'].encode('utf-8'),
          request.POST['slave_code'].encode('utf-8'))

    dest = reverse('board', kwargs={'key':request.POST['slave_id']})
    return redirect(dest)
