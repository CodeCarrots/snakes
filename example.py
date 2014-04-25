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

def find_head(board):
    for i, row in enumerate(board):
        for j, letter in enumerate(row):
            if letter == 'H':
                return j, i

def move(board):
    head = find_head(board)
    goto = random.choice(['left', 'right', 'up', 'down'])
    choices = [
            ('left', -1, 0),
            ('right', 1, 0),
            ('up', 0, -1),
            ('down', 0, 1),
        ]
    random.shuffle(choices)
    for (direction, dx, dy) in choices:
        new_head = (head[0]+dx, head[1]+dy)
        if new_head[0] < 0:
            continue
        if new_head[1] < 0:
            continue
        if new_head[0] > WIDTH - 1:
            continue
        if new_head[1] > HEIGHT - 1:
            continue
        if board[new_head[1]][new_head[0]] == '#':
            continue
        goto = direction
    return goto

# Don't touch (unless you know what you're doing :-))
while True:
    board = [sys.stdin.readline() for _ in range(HEIGHT)]
    sys.stdout.write(move(board))
    sys.stdout.write('\\n')
