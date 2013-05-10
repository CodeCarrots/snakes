import redis
from flask import Flask, render_template

app = Flask(__name__)

r = redis.StrictRedis(host='localhost', port=6379, db=0)

@app.route("/")
def board():
    return render_template('board.html', board=r.get('board'))


if __name__ == '__main__':
    app.run()
