import redis
import json
from flask import Flask, render_template, request, redirect, url_for


app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)


@app.route('/')
@app.route('/snake/<key>')
def board(key=None):
    return render_template('board.html', board=r.get('board'), key=key)


@app.route('/board')
@app.route('/board/<key>')
def check_board(key=None):
    return r.get('snakes') or json.dumps({'snakes': [{'parts': [[1, 1], [1, 2], [2, 2]]}], 'apples': []})


@app.route('/reload_slave', methods=['POST'])
def reload_code():
    if (';' in request.form['slave_name']
        or len(request.form['slave_id']) == 0
        or len(request.form['slave_name']) == 0
        or len(request.form['slave_code']) == 0):
        return redirect(url_for('board'))
    command = 'reload_slave;%s;%s;%s' % (request.form['slave_id'],
                                         request.form['slave_name'],
                                         request.form['slave_code'])
    r.rpush('commands', command)
    return redirect(url_for('board', key=request.form['slave_id']))


if __name__ == '__main__':
    app.run(debug=True)
