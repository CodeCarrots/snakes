from judge import SnakeJudge

SCRIPT = r"""
import sys
for i in range(10):
    sys.stdout.write('alamakota\n')
    text = sys.stdin.readline()
    sys.stdout.write(text)
"""

SCRIPT2 = r"""
import sys, random
while True:
    for x in range(60):
        sys.stdin.readline()
    sys.stdout.write(random.choice(['left', 'right', 'up', 'down']))
    sys.stdout.write('\n')
"""

SCRIPT3 = r"""
import sys, random

def get_head(board):
    for y, row in enumerate(board):
        for x, field in enumerate(row):
            if field == 'H':
                return (x, y)

def possible_moves(board):
    height = len(board)
    width = len(board[0])
    head = get_head(board)
    moves = [(-1, 0, 'left'), (1, 0, 'right'), (0, -1, 'up'), (0, 1, 'down')]
    result = []
    for move in moves:
        if (0 <= head[0] + move[0] < width
            and 0 <= head[1] + move[1] < height
            and board[head[1] + move[1]][head[0] + move[0]] != '#'):
            result.append(move[2])
    return result

while True:
    board = []
    for _ in range(60):
        board.append(sys.stdin.readline()[:-1])

    moves = possible_moves(board)
    sys.stdout.write(random.choice(moves) if len(moves) > 0 else 'right')
    sys.stdout.write('\n')
"""

judge = SnakeJudge(80, 60)
for i in range(3):
    judge.add_slave(SCRIPT3)
for i in range(6):
    judge.add_slave(SCRIPT2)
judge.run()
