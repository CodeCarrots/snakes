import redis
import json
from flask import Flask, render_template, request, redirect, url_for


app = Flask(__name__)
r = redis.StrictRedis(host='localhost', port=6379, db=0)


@app.route('/')
def board():
    return render_template('board.html', board=r.get('board'))


@app.route('/board')
def check_board():
    return r.get('board')
    # return r.get('snakes') or json.dumps({'snakes': []})


@app.route('/reload_code', methods=['POST'])
def reload_code():
    if ';' in request.form['slave_name']:
        return redirect(url_for('board'))
    command = 'reload_code;%s;%s;%s' % (request.form['slave_id'],
                                        request.form['slave_name'],
                                        request.form['slave_code'])
    r.rpush('commands', command)
    return redirect(url_for('board'))


if __name__ == '__main__':
    app.run()
