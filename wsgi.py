import redis
import json
from flask import Flask, render_template, request, redirect, url_for
from flask import Response

app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)


SCRIPT = """\
import sys, random

WIDTH, HEIGHT = 80, 60

# Change here!
# ------------
# Board is a list of strings (board rows), where:
#  - o = apple
#  - # = snake
#  - H = head of our snake
#  - . = empty field
#
# Move should return 'left', 'right', 'up' or 'down'
def move(board):
    return random.choice(['left', 'right', 'up', 'down'])

# Don't touch (unless you know what you're doing :-))
while True:
    board = [sys.stdin.readline() for _ in range(HEIGHT)]
    sys.stdout.write(move(board))
    sys.stdout.write('\\n')
"""

def tail( f, window=20 ):
    BUFSIZ = 1024
    f.seek(0, 2)
    bytes = f.tell()
    size = window
    block = -1
    data = []
    while size > 0 and bytes > 0:
        if (bytes - BUFSIZ > 0):
            # Seek back one whole BUFSIZ
            f.seek(block*BUFSIZ, 2)
            # read BUFFER
            data.append(f.read(BUFSIZ))
        else:
            # file too small, start from begining
            f.seek(0,0)
            # only read what was not read
            data.append(f.read(bytes))
        linesFound = data[-1].count('\n')
        size -= linesFound
        bytes -= BUFSIZ
        block -= 1
    return '\n'.join(''.join(data).splitlines()[-window:])


@app.route('/log')
def log():
    return Response(tail(file('/srv/webapps/snakes/log/judge.log'), 1000), mimetype='text/plain')


@app.route('/')
@app.route('/snake/<key>')
def board(key=None):
    snake_name = 'Annonymous'
    snake_code = SCRIPT
    snake_color = '#fff'

    if key is not None:
        snake_name = (r.get('snake:%s:name' % key) or '').decode('utf-8')
        snake_code = (r.get('snake:%s:code' % key) or SCRIPT).decode('utf-8')
        snake_color = (r.get('snake:%s:color' % key) or '#fff').decode('utf-8')
    return render_template('board.html',
                           board=r.get('board'),
                           key=key or '',
                           name=snake_name,
                           code=snake_code,
                           color=snake_color)


@app.route('/board')
def check_board():
    snakes = r.get('snakes')
    if snakes is not None:
        return snakes.decode('utf-8')
    else:
        return json.dumps({'snakes': []})


def snake_name(key):
    name = r.get('snake:%s:name' % key)
    if name is not None:
        return name.decode('utf-8')
    else:
        return u'Annonymous'


@app.route('/leaderboard')
def leaderboard():
    return render_template('leaderboard.html', members=[
        {'name': snake_name(s[0]), 'score': int(s[1])}
        for s in r.zrevrange('leaderboard', 0, -1, withscores=True)])


@app.route('/reload_slave', methods=['POST'])
def reload_code():
    if (';' in request.form['slave_name']
        or len(request.form['slave_id']) == 0
        or len(request.form['slave_name']) == 0
        or len(request.form['slave_code']) == 0):
        return redirect(url_for('board'))
    command = u'reload_slave;%s;%s;%s' % (request.form['slave_id'],
                                          request.form['slave_name'],
                                          request.form['slave_code'])
    r.rpush('commands', command.encode('utf-8'))
    r.set('snake:%s:name' % request.form['slave_id'].encode('utf-8'),
          request.form['slave_name'].encode('utf-8'))
    r.set('snake:%s:code' % request.form['slave_id'].encode('utf-8'),
          request.form['slave_code'].encode('utf-8'))

    return redirect(url_for('board', key=request.form['slave_id']))


if __name__ == '__main__':
    app.run()
