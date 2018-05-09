import sys
import random

WIDTH, HEIGHT = {WIDTH}, {HEIGHT}

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
    board = [sys.stdin.readline().rstrip('\n') for _ in range(HEIGHT)]
    sys.stdout.write(move(board))
    sys.stdout.write('\n')
