import os
import pwd
import random
import resource
import shutil
import signal
import stat
import StringIO
import subprocess
import sys
import threading
import time
from collections import namedtuple, deque, defaultdict

import redis


JAIL_ROOT = '/jail/cells'
JAIL_ZYGOTE = '/jail/zygote'
SLAVE_GROUP = 'slaves'
SLAVE_USERNAME_PATTERN = 'slave{:02d}'


def safe_makedirs(path, mode=0o777):
    try:
        os.makedirs(path, mode)
    except OSError as e:
        if e.errno != 17: # 17 == directory already exists
            raise


def create_slave_group():
    try:
        subprocess.check_call(['addgroup',
                               '--system', SLAVE_GROUP])
    except subprocess.CalledProcessError as e:
        if e.returncode != 1: # group already exists?
            raise
    if subprocess.call(['iptables',
                        '-C', 'OUTPUT',
                        '-m', 'owner',
                        '--gid-owner', SLAVE_GROUP,
                        '-j', 'DROP']) != 0:
        subprocess.check_call(['iptables',
                               '-A', 'OUTPUT',
                               '-m', 'owner',
                               '--gid-owner', SLAVE_GROUP,
                               '-j', 'DROP'])


def create_slave_env(name):
    cell = os.path.join(JAIL_ROOT, name)

    # Create user
    subprocess.check_call(['/usr/sbin/adduser',
                           '--system',
                           '--ingroup', SLAVE_GROUP,
                           '--home', cell,
                           '--shell', '/bin/false',
                           '--no-create-home',
                           '--disabled-password',
                           name])

    # Copy chroot zygote to users home and change permissions
    safe_makedirs(JAIL_ROOT, mode=0o755)
    shutil.copytree(JAIL_ZYGOTE, cell)

    os.chmod(cell , 0o755)
    for root, dirs, files in os.walk(cell):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)
        for f in files:
            os.chmod(os.path.join(root, f), 0o755)

    # Create random and urandom devices
    safe_makedirs(os.path.join(cell, 'dev'), 0o755)
    os.mknod(os.path.join(cell, 'dev', 'random'), 0o644 | stat.S_IFCHR, os.makedev(1, 8))
    os.mknod(os.path.join(cell, 'dev', 'urandom'), 0o644 | stat.S_IFCHR, os.makedev(1, 9))


def get_process_children(pid):
    p = subprocess.Popen('ps --no-headers -o pid --ppid %d' % pid, shell=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return [int(p) for p in stdout.split()]




class Slave(object):
    def __init__(self, env, script):
        self.env = env
        self.script = script
        self.cell = os.path.join(JAIL_ROOT, self.env)
        self.stderr = StringIO.StringIO()

    def instrument_process(self):
        uid = pwd.getpwnam(self.env).pw_uid
        os.chdir(self.cell)
        os.chroot(self.cell)

        resource.setrlimit(resource.RLIMIT_DATA, (32 * 1024 * 1024, 32 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_STACK, (8 * 1024 * 1024, 8 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
        os.nice(15)

        os.setuid(uid)

    def run(self):
        with file(os.path.join(self.cell, 'script.py'), 'w') as f:
            f.write(self.script)
        os.chmod(os.path.join(self.cell, 'script.py'), 0o755)
        self.process = subprocess.Popen(['./python', 'script.py'],
                                        shell=False,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=sys.stderr,
                                        env={'PYTHONUSERBASE': '/nonexistent',
                                             'PYTHONUNBUFFERED': 'x'},
                                        close_fds=True,
                                        preexec_fn=self.instrument_process)
        os.kill(self.process.pid, signal.SIGSTOP)

    def kill_process(self, kill_tree=True):
        pids = [self.process.pid]
        if kill_tree:
            pids.extend(get_process_children(self.process.pid))
        for pid in pids:
            # process might have died before getting to this line
            # so wrap to avoid OSError: no such process
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass

    def send(self, message, timeout=0):
        """Sends a message to the slave and returns response."""
        if timeout > 0:
            timer = threading.Timer(timeout, self.kill_process)
            timer.start()

        try:
            os.kill(self.process.pid, signal.SIGCONT)
            self.process.stdin.write(message)
            result = self.process.stdout.readline()
        except OSError:
            # process has died
            return ''
        finally:
            # process might have died before getting to this line
            # so wrap to avoid OSError: no such process
            try:
                os.kill(self.process.pid, signal.SIGSTOP)
            except OSError:
                pass
            if timeout > 0:
                timer.cancel()

        return result

    def __repr__(self):
        pr = ''
        if hasattr(self, 'process') and self.process.pid:
            retval = self.process.poll()
            if retval is None:
                pr = ' [process %d RUNNING]' % self.process.pid
            else:
                pr = ' [process %d RET %d]' % (self.process.pid, retval)
        return 'Slave(%s)%s' % (self.env, pr)


class Judge(object):
    def __init__(self):
        create_slave_group()
        self.slaves = []

    def add_slave(self, args):
        slave_name = SLAVE_USERNAME_PATTERN.format(len(self.slaves) + 1)
        create_slave_env(slave_name)
        self.slaves.append(Slave(slave_name, args))

    def run(self):
        for slave in self.slaves:
            slave.run()
        while True:
            for slave in self.slaves:
                print slave, slave.send('ping\n', 5)
                time.sleep(0.5)


Point = namedtuple('Point', ['x', 'y'])


class Board(object):
    def __init__(self, width=10, height=10):
        self.width = width
        self.height = height
        self.fields = [['.'] * width for _ in range(height)]
        self.empty_fields = set(Point(x, y) for x in range(width) for y in range(height))

    def __getitem__(self, (x, y)):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return '#'
        return self.fields[y][x]

    def __setitem__(self, (x, y), value):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return

        self.fields[y][x] = value

        if value == '.':
            self.empty_fields.add(Point(x, y))
        else:
            self.empty_fields.discard(Point(x, y))

    def random_empty_field(self):
        if len(self.empty_fields) == 0:
            return None
        return random.sample(self.empty_fields, 1)[0]

    def __str__(self):
        result = []
        for row in self.fields:
            result.append(''.join(row))
        return '\n'.join(result)


class Snake(object):
    def __init__(self, parts=None, direction=None):
        self.parts = deque(parts) if parts is not None else deque([Point(4, 4)])
        self.direction = direction if direction is not None else 'right'
        self.ate_apple = False
        self.dead = False

    @property
    def head(self):
        return self.parts[-1]

    def grow(self):
        new_part = {'up': Point(self.head.x, self.head.y - 1),
                    'down': Point(self.head.x, self.head.y + 1),
                    'left': Point(self.head.x - 1, self.head.y),
                    'right': Point(self.head.x + 1, self.head.y)}[self.direction]
        self.parts.append(new_part)
        return new_part

    def shrink(self):
        return self.parts.popleft()

    def move(self):
        if self.dead:
            return (None, None)
        added = self.grow()
        removed = None
        if not self.ate_apple:
            removed = self.shrink()
        self.ate_apple = False
        return (added, removed)


class SnakeJudge(Judge):
    def __init__(self, width=10, height=10):
        super(SnakeJudge, self).__init__()
        self.width = width
        self.height = height
        self.board = Board(width, height)
        self.turn = 0
        self.snakes = []
        self.r = redis.StrictRedis(host='localhost', port=6379, db=0)

    def add_slave(self, args):
        super(SnakeJudge, self).add_slave(args)
        self.spawn_snake()

    def spawn_snake(self):
        p = self.board.random_empty_field()
        self.board[p.x, p.y] = '#'
        self.snakes.append(Snake([p]))

    def spawn_apple(self):
        p = self.board.random_empty_field()
        self.board[p.x, p.y] = 'o'

    def kill_snake(self, snake):
        for p in snake.parts:
            self.board[p.x, p.y] = '.'
        snake.dead = True

    def check_collisions(self, heads, removed):
        for p in removed:
            self.board[p.x, p.y] = '.'

        for p, snakes in heads.items():
            # Check collisions between heads
            if len(snakes) > 1:
                for snake in snakes:
                    self.kill_snake(snake)
                continue

            # Check collisions between other parts
            if self.board[p.x, p.y] == '#':
                for snake in snakes:
                    self.kill_snake(snake)
                continue

            # Check collisions with apples
            if self.board[p.x, p.y] == 'o':
                for snake in snakes:
                    snake.ate_apple = True
            self.board[p.x, p.y] = '#'

        if self.turn % 5 == 0:
            self.spawn_apple()
        self.turn += 1

    def run(self):
        for slave in self.slaves:
            slave.run()
        while True:
            heads = defaultdict(list)
            removed = []
            for slave, snake in zip(self.slaves, self.snakes):
                print slave,
                if snake.dead:
                    print 'DEAD'
                    slave.kill_process()
                    continue
                if slave.process.poll() is not None:
                    print 'DEAD'
                    snake.dead = True
                    continue
                self.board[(snake.head.x, snake.head.y)] = 'H'
                r = slave.send(str(self.board) + '\n', 5)
                self.board[(snake.head.x, snake.head.y)] = '#'
                print r
                if r[:-1] not in ('left', 'right', 'up', 'down'):
                    slave.kill_process()
                    snake.dead = True
                    continue
                snake.direction = r[:-1]
                head, tail = snake.move()
                if head != None:
                    heads[head].append(snake)
                if tail != None:
                    removed.append(tail)
            self.check_collisions(heads, removed)
            print str(self.board)
            print
            print
            self.r.set('board', str(self.board))
            time.sleep(1)
