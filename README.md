snakes
======

Corewars-like snakes game server. It implements a multi-player
environment for a [Snake-like][1] game in which each snake is
controlled by a computer program written in [Python][2].


[1]: https://en.wikipedia.org/wiki/Snake_(video_game_genre)
[2]: https://www.python.org/


Game rules
----------

Some specifics of the implemented variant:

- all snakes occupy the same single board and move simultaneously in
  synchronized discreete-time steps;

- snake dies if its head attempts to leave the board boundaries or
  move to a field occupied by a snake (including itself);

- snake dies if its program attempts to perform an illegal or
  unrecognized move;

- snake dies when a new version of its code is submitted;

- snake dies when it "thinks too long" on a move (when its controlling
  program takes too long to provide a move after receiving the board
  state);

- for each snake the server keeps score - the snake's maximum achieved
  length;

- when a snake dies it is removed from the board, its length is reset
  to 1 and it "re-spawns" on a random field in the next time step;

- the snake's score is preserved when it dies.


Users/contestants
-----------------

Each contestant starts with an example program controlling their
snake. The example program has a commented "scaffolding" and
implements a simple "choose-a-random-direction" strategy in its
`move()` function.

Your goal is to implement a better strategy for your snake - you can
use all the power of the language, including using builtin modules. In
the provided scaffolding code the `move()` function is called once per
time step, its input is the current `board` state represented as a
list of strings, e.g.:

```python
['.###.....',
 '.o....#..',
 '......#..',
 '..o.###..',
 '....#...o',
 '....#H...']
```

Each character in the board representation describes a sigle board field:

- `.`: empty field - safe to move there;

- `o`: apple - eat those to grow your snake! (and possibly your score,
  too!);

- `H`: the head of your snake - there's always exactly one `H` on the
  board;

- `#`: part of a snake, yours or opponent's.

Each time your `move()` function is called it should return a string
describing a valid move. Valid moves are: `left`, `right`, `up`,
`down`.


Mentors
-------

Each snake is run in a separate process, in an enviroment that
attempts to provide isolation from other snakes' processes - the goal
is for the contestants to win by implementing a better algorithm and
not by hacking other snakes ;)

The game server communicates with each snake process by sending board
state updates on `stdin` and expecting a valid move written to
`stdout` after each board update, within certain time-frame. Anything
the snake process writes to `stderr` is collected and shown in the
user's web client window - you can use that for debugging user
scripts.

Snake process is killed and re-created when the snake dies. It can
also be killed for other reasons, e.g. server restart. The board
state, snake scores and user scripts' code is preserved but the state
of the snake process is not. So, implementing solutions that attempt
to store and remember state between time steps might not be such a
good idea.


Admin
-----

The server's runtime consists of at least 3 processes: redis server,
snakes manager server and a django server. You might want a front-end
HTTP server, as well. The snake manager server requires some pretty
specific enviroment to do its job properly - see [snakes-docker][1]
for some help setting-up and running.

Once everything is running, managing the game is done through the
`snakes-manage` script (run in a way that allows it to communicate
with the redis server). Add some snakes with `snakes-manage add_snake
...` ("snake key" should be a random string, preferably of length 6+,
that acts as a snake identificator and a password at the same time,
should be kept somewhat secret) then get the unique urls for them with
`snakes-manage players ...`.

`-h` is your friend.


[1]: https://github.com/CodeCarrots/snakes-docker
