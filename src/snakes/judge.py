from __future__ import print_function

import colorsys
import os
import pwd
import grp
import random
import resource
import signal
import stat
from io import StringIO
import subprocess
import threading
import time
import json
import fcntl
import queue as Queue
from collections import namedtuple, deque, defaultdict
import redis
import codecs
import logging
from .db import get_db
from snakes.example import get_example, WIDTH, HEIGHT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


JAIL_ROOT = '/jail/cells'
JAIL_ZYGOTE = '/jail/zygote'
SLAVE_GROUP = 'slaves'
SLAVE_USERNAME_PATTERN = 'slave{:02d}'


def safe_makedirs(path, mode=0o777):
    try:
        os.makedirs(path, mode)
    except OSError as e:
        if e.errno != 17:  # 17 == directory already exists
            raise


def run_command(*args):
    print("Running ", args[0])
    return subprocess.check_call(*args)


def create_slave_group():
    try:
        run_command(['addgroup',
                     '--system', SLAVE_GROUP])
    except subprocess.CalledProcessError as e:
        if e.returncode != 1: # group already exists?
            raise
    # if subprocess.call(['iptables',
    #                     '-C', 'OUTPUT',
    #                     '-m', 'owner',
    #                     '--gid-owner', SLAVE_GROUP,
    #                     '-j', 'DROP']) != 0:
    #     subprocess.check_call(['iptables',
    #                            '-A', 'OUTPUT',
    #                            '-m', 'owner',
    #                            '--gid-owner', SLAVE_GROUP,
    #                            '-j', 'DROP'])


def create_slave_env(name):
    cell = os.path.join(JAIL_ROOT, name)
    if os.path.exists(cell):
        return

    safe_makedirs(JAIL_ROOT, mode=0o755)
    safe_makedirs(cell)
    safe_makedirs(os.path.join(cell, 'bin'))
    safe_makedirs(os.path.join(cell, 'lib'))
    safe_makedirs(os.path.join(cell, 'lib64'))
    safe_makedirs(os.path.join(cell, 'usr'))
    run_command([
        'ln',
        os.path.join(JAIL_ZYGOTE, 'python'),
        os.path.join(cell, 'python')
    ])
    run_command([
        'mount', '--bind',
        os.path.join(JAIL_ZYGOTE, 'bin'),
        os.path.join(cell, 'bin')
    ])
    run_command([
        'mount', '--bind',
        os.path.join(JAIL_ZYGOTE, 'lib'),
        os.path.join(cell, 'lib')
    ])
    run_command([
        'mount', '--bind',
        os.path.join(JAIL_ZYGOTE, 'lib64'),
        os.path.join(cell, 'lib64')
    ])
    run_command([
        'mount', '--bind',
        os.path.join(JAIL_ZYGOTE, 'usr'),
        os.path.join(cell, 'usr')
    ])
    # Create user
    run_command(['/usr/sbin/adduser',
                           '--system',
                           '--ingroup', SLAVE_GROUP,
                           '--home', cell,
                           '--shell', '/bin/false',
                           '--no-create-home',
                           '--disabled-password',
                           name])

    os.chmod(cell, 0o755)
    print("chmod", cell)
    for root, dirs, files in os.walk(cell):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)
        for f in files:
            os.chmod(os.path.join(root, f), 0o755)

    # Create random and urandom devices
    safe_makedirs(os.path.join(cell, 'dev'), 0o755)
    print("mkdir dev", cell)
    try:
        os.mknod(os.path.join(cell, 'dev', 'random'),
                 0o644 | stat.S_IFCHR, os.makedev(1, 8))
        os.mknod(os.path.join(cell, 'dev', 'urandom'),
                 0o644 | stat.S_IFCHR, os.makedev(1, 9))
    except OSError:
        pass
    print("slave env created", cell)


def get_process_children(pid):
    process = subprocess.Popen('ps --no-headers -o pid --ppid %d' % pid,
                               shell=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    return [int(p) for p in stdout.split()]


class Slave(object):
    def __init__(self, env, script, slot):
        self.env = env
        self.script = script
        self.cell = os.path.join(JAIL_ROOT, self.env)
        self.stderr = StringIO()
        self.last_err = ''
        self.slot = slot
        self.uid = pwd.getpwnam(self.env).pw_uid
        self.gid = grp.getgrnam(SLAVE_GROUP).gr_gid

    def instrument_process(self):
        os.chdir(self.cell)
        os.chroot(self.cell)

        resource.setrlimit(resource.RLIMIT_DATA,
                           (32 * 1024 * 1024, 32 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_STACK,
                           (8 * 1024 * 1024, 8 * 1024 * 1024))
        # resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
        os.nice(15)

        os.setgroups([])
        os.setgid(self.gid)
        os.setuid(self.uid)

    def run(self):
        with codecs.open(os.path.join(self.cell, 'script.py'), 'w',
                         encoding='utf-8') as f:
            f.write(self.script)
        os.chmod(os.path.join(self.cell, 'script.py'), 0o755)
        logger.info("running %s" % (self.cell,))
        self.process = subprocess.Popen(['./python', 'script.py'],
                                        shell=False,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        env={'PYTHONUSERBASE': '/nonexistent',
                                             'PYTHONUNBUFFERED': 'x'},
                                        close_fds=True,
                                        preexec_fn=self.instrument_process)
        fcntl.fcntl(self.process.stderr.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
        os.kill(self.process.pid, signal.SIGSTOP)

    def kill_process(self, kill_tree=True):
        self.last_err = ''
        if not hasattr(self, 'process'):
            return
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
        self.process.wait()

    def send(self, message, timeout=0):
        """Sends a message to the slave and returns response."""
        timer = None
        if timeout > 0:
            timer = threading.Timer(timeout, self.kill_process)
            timer.start()
        result = ''
        err = ''
        try:
            try:
                os.kill(self.process.pid, signal.SIGCONT)
            except OSError as exc:
                logger.exception("Failed to resume %s" % (self.cell,))
                return '', ''
            try:
                self.process.stdin.write(message.encode('utf-8'))
            except IOError as exc:
                logger.exception("Failed to communicate with %s" % (self.cell,))
                return '', ''

            try:
                result = self.process.stdout.readline().decode('utf-8')
                err = self.process.stderr.read()
                if err is not None:
                    err = err.decode('utf-8')
            except IOError as exc:
                if exc.errno == 11:
                    pass
                else:
                    return '', ''
        finally:
            try:
                os.kill(self.process.pid, signal.SIGSTOP)
            except OSError:
                pass
            if timeout > 0:
                timer.cancel()

        return result.strip().lower(), err

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
        self.used_slots = set()

    def get_free_slot(self):
        i = 0
        while True:
            if i not in self.used_slots:
                break
            i += 1
        self.used_slots.add(i)
        return i

    def add_slave(self, slave_code):
        slot = self.get_free_slot()
        slave_name = SLAVE_USERNAME_PATTERN.format(slot)
        create_slave_env(slave_name)
        slave = Slave(slave_name, slave_code, slot)
        self.slaves.append(slave)
        return slave

    def remove_slave(self, slave):
        self.slaves.remove(slave)
        self.used_slots.remove(slave.slot)

    def run(self):
        for slave in self.slaves:
            slave.run()
        while True:
            for slave in self.slaves:
                print(slave, slave.send('ping\n', 5))
                time.sleep(0.5)


Point = namedtuple('Point', ['x', 'y'])


class Board(object):
    def __init__(self, width=10, height=10):
        self.width = width
        self.height = height
        self.fields = [['.'] * width for _ in range(height)]
        self.h_x = None
        self.h_y = None
        # self.empty_fields = set(Point(x, y) for x in range(width)
        #                         for y in range(height))
        self.apples = set()

    def copy(self):
        board = Board(self.width, self.height)
        board.fields = self.fields
        #board.fields = [list(x) for x in self.fields]
        #board.empty_fields = set(self.empty_fields)
        board.apples = set(self.apples)
        return board

    def __getitem__(self, x_y):
        (x, y) = x_y
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return '#'
        if x == self.h_x and y == self.h_y:
            return 'H'
        return self.fields[y][x]

    def __setitem__(self, x_y, value):
        (x, y) = x_y
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return

        if value != 'H':
            self.fields[y][x] = value
        else:
            self.h_x = x
            self.h_y = y

        if value == 'o':
            self.apples.add(Point(x, y))
        else:
            self.apples.discard(Point(x, y))

        #if value == '.':
        #    self.empty_fields.add(Point(x, y))
        #else:
        #    self.empty_fields.discard(Point(x, y))

    def random_empty_field(self):
        #if len(self.empty_fields) == 0:
        #    return None
        for i in range(100):
            x = random.randrange(self.width)
            y = random.randrange(self.height)
            if self[(x, y)] == '.':
                return Point(x, y)
        # return random.sample(self.empty_fields, 1)[0]

    def apples(self):
        return self.apples

    def __str__(self):
        result = []
        for y, row in enumerate(self.fields):
            if y ==  self.h_y:
                row = list(row)
                row[self.h_x] = 'H'
            result.append(''.join(row))
        return '\n'.join(result)


class Snake(object):
    def __init__(self, parts=None, direction=None, color=None,
                 name='annonymous', key=None):
        self.parts = deque(parts) if parts is not None else deque([Point(4, 4)])
        self.direction = direction if direction is not None else 'right'
        self.ate_apple = False
        self.dead = False
        self.name = name
        self.color = color
        self.key = key

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
            return None, None
        added = self.grow()
        removed = None
        if not self.ate_apple:
            removed = self.shrink()
        self.ate_apple = False
        return added, removed

    def as_dict(self):
        return {'name': self.name,
                'parts': [[p.x, p.y] for p in self.parts],
                'dead': self.dead,
                'key': self.key,
                'color': self.color}


class Worker(threading.Thread):

    def __init__(self, tasks):
        super(Worker, self).__init__()
        self.tasks = tasks
        self.daemon = True
        self.stopped = False
        self.start()

    def run(self):
        while not self.stopped:
            func, args, kargs = self.tasks.get()
            try:
                func(*args, **kargs)
            except Exception as exc:
                logger.exception("Error while executing task\n%r\n%r",
                                 args, kargs)
            self.tasks.task_done()


class SnakeJudge(Judge):
    def __init__(self, width=10, height=10, threads=4):
        super(SnakeJudge, self).__init__()
        self.commands = Queue.Queue()
        self.width = width
        self.height = height
        self.board = Board(width, height)
        self.turn = 0
        self.snakes = {}
        self.r = get_db()
        self.leaderboard = {key.decode('utf-8'): score
                            for (key, score)
                            in self.r.zrevrange('leaderboard', 0, -1,
                                                withscores=True)}
        self._load_snakes()
        self._threads = threads

    def _load_snakes(self):
        keys = self.r.smembers('keys')
        for key in keys:
            self.command_add_snake(key.decode('utf-8'))

    def add_slave_snake(self, script, key, color):
        slave = super(SnakeJudge, self).add_slave(script)
        snake = self.spawn_snake(color, key=key)
        self.snakes[key] = (slave, snake)
        return key

    def spawn_snake(self, color, key):
        p = self.board.random_empty_field()
        self.board[p.x, p.y] = '#'
        return Snake([p], color=color, key=key)

    def spawn_apple(self):
        p = self.board.random_empty_field()
        if p is not None:
            self.board[p.x, p.y] = 'o'

    def kill_snake(self, snake, clear=False):
        if snake.dead:  # Can't kill dead snake
            return
        snake.dead = True
        if not clear:
            return
        for p in snake.parts:
            self.board[p.x, p.y] = '.'

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
        
        board = Board(self.width, self.height)
        for snake in self.snakes.values():
            snake = snake[1]
            for part in snake.parts:
                board[part.x, part.y] = '#'
                
        for apple in self.board.apples:
            board[apple.x, apple.y] = 'o'
        self.board = board
        if len(self.board.apples) < 10:
            self.spawn_apple()
        elif self.turn % 1 == 0:
            self.spawn_apple()
        self.turn += 1

    def as_dict(self):
        return {'snakes': [s[1].as_dict() for s in self.snakes.values()],
                'apples': [[p.x, p.y] for p in self.board.apples]}

    def clear_leaderboard(self):
        self.r.delete('leaderboard')
        for key, (slave, snake) in self.snakes.items():
            self.leaderboard[key] = 0
            self.r.zadd('leaderboard', 0, key)

    def reset_snake(self, snake, slave, key):
        self.kill_snake(snake, clear=True)
        self.snakes[key] = (slave, self.spawn_snake(snake.color, key=key))
        slave.script = self.get_snake_code(key)
        slave.kill_process()
        slave.run()

    def command_reset(self):
        self.board = Board(self.width, self.height)
        for key, (slave, snake) in self.snakes.items():
            self.reset_snake(snake, slave, key)
        self.clear_leaderboard()

    def command_reload_slave(self, slave_id, slave_name, slave_code):
        slave, snake = self.snakes.get(slave_id, (None, None))
        if slave is not None:
            snake.name = slave_name
            slave.script = slave_code
            slave.kill_process()
            self.r.set('snake:%s:err' % (slave_id,), '')

    def command_remove_snake(self, key):
        if key not in self.snakes:
            return
        slave, snake = self.snakes[key]
        self.kill_snake(snake, clear=True)
        slave.kill_process()
        del self.snakes[key]
        del self.leaderboard[key]
        self.r.zrem('leaderboard', key)
        self.r.srem("keys", key)
        self.remove_slave(slave)

    def get_snake_code(self, key):
        script = self.r.get('snake:%s:code' % key)
        if script is None:
            logger.info("Loaded code for %s from example" % (key,))
            script = get_example()
            self.r.set('snake:%s:code' % key, script.encode('utf-8'))
        else:
            logger.info("Loaded code for %s from database" % (key,))
            script = script.decode('utf-8')
        return script

    def command_add_snake(self, key):
        if key in self.snakes:
            return
        self.r.sadd("keys", key)
        color = self.r.get('snake:%s:color' % key)
        if color is None:
            h = random.random()
            s = 1
            v = 0.8
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            color = ('#%02x%02x%02x' % (int(r*255), int(g*255),
                                        int(b*255))).lower()
        else:
            color = color.decode('utf-8')

        self.r.set('snake:%s:color' % key, color)
        script = self.get_snake_code(key)
        name = self.r.get('snake:%s:name' % key)
        if name is None:
            self.r.set('snake:%s:name' % key, u'Anonymous')
        self.add_slave_snake(script, key, color=color)
        slave, snake = self.snakes[key]
        slave.run()

    def run_commands(self):
        try:
            while True:
                command_args = self.commands.get_nowait()
                command = command_args[0]
                args = command_args[1:]
                if command == 'reload_slave':
                    slave_id, slave_name, slave_code = args
                    self.command_reload_slave(slave_id, slave_name, slave_code)
                if command == 'reset':
                    self.command_reset()
                if command == 'remove_snake':
                    key = args[0]
                    self.command_remove_snake(key)
                if command == 'add_snake':
                    key = args[0]
                    self.command_add_snake(key)
        except Queue.Empty:
            pass

    def update_leaderboard(self):
        for key, (slave, snake) in self.snakes.items():
            if self.leaderboard.get(key, 0) < len(snake.parts):
                self.leaderboard[key] = len(snake.parts)
                self.r.zadd('leaderboard', len(snake.parts), key)

    def move_snake(self, key, slave, snake):
        logger.debug("%s: %s" % (key[:3], slave))
        if slave.process.poll() is not None:
            logger.info("%s: DEAD - process" % (key,))
            logger.info("%s: Reviving..." % (key,))
            self.kill_snake(snake, clear=True)
            self.snakes[key] = (slave, self.spawn_snake(snake.color, key=key))
            slave.run()
            return

        if snake.dead:
            logger.info("%s: DEAD - collision?" % (key,))
            slave.kill_process()
            return
        board = self.board.copy()
        board[(snake.head.x, snake.head.y)] = 'H'
        r, err = slave.send(str(board) + '\n', 5)
        #self.board[(snake.head.x, snake.head.y)] = '#'
        logger.debug("%s: move %s" % (key, r[:50]))

        if err is not None:
            previous_errors = self.r.get('snake:%s:err' % (key,)) or b''
            previous_errors = previous_errors.decode('utf-8') + err
            previous_errors = previous_errors.split('\n')[-1000:]
            errors = u"\n".join(previous_errors)
            self.r.set('snake:%s:err' % (key,), errors.encode('utf-8'))

        # message = ''
        if r not in ('left', 'right', 'up', 'down'):
            logger.info("%s: killing because %r is not a direction",
                        key, r[:50])
            slave.kill_process()
            self.kill_snake(snake, clear=True)
            # if r:
            #     message = 'Received invalid command %r\n' % (r,)
            return

        snake.direction = r
        head, tail = snake.move()
        return head, tail

    def wait(self, delay):
        now = time.time()
        wait_until = self.start + delay
        if now <= wait_until:
            real_delay = wait_until - now
            logger.info('sleeping %.3fs...', real_delay)
            time.sleep(real_delay)
        else:
            logger.info('not sleeping')
        self.start = wait_until

    def run_infinite(self, queue):
        self.start = time.time()
        while True:
            self.run_commands()
            heads = defaultdict(list)
            removed = []
            for key, (slave, snake) in self.snakes.items():

                def slave_step(key_, slave_, snake_):
                    head_tail = self.move_snake(key_, slave_, snake_)
                    if head_tail is None:
                        return
                    head, tail = head_tail
                    if head is not None:
                        heads[head].append(snake_)
                    if tail is not None:
                        removed.append(tail)
                queue.put((slave_step, (key, slave, snake), {}))

            queue.join()
            self.check_collisions(heads, removed)
            self.r.set('board', str(self.board))
            self.r.set('snakes', json.dumps(self.as_dict()))
            self.update_leaderboard()
            self.wait(1)

    def run(self):
        # for slave in self.slaves:
        #     slave.run()

        queue = Queue.Queue()
        threads = []
        for i in range(self._threads):
            thread = Worker(queue)
            threads.append(thread)
        try:
            self.run_infinite(queue)
        except KeyboardInterrupt:
            pass

        for thread in threads:
            thread.stopped = True
        for thread in threads:
            queue.put((lambda: None, (), {}))
        for thread in threads:
            thread.join()


# class MultiBoardJudge(object):
#
#     def __init__(self, r):
#         self.r = r
#
#     def command_create_board(self, name):
#         pass
#
#     def command_reload_snake(self, slave_id, slave_name, slave_code):
#         slave, snake = self.snakes.get(slave_id, (None, None))
#         if slave is not None:
#             snake.name = slave_name
#             slave.script = slave_code
#             slave.kill_process()
#             self.r.set('snake:%s:err' % (slave_id,), '')
#
#     def run_commands(self):
#         try:
#             while True:
#                 command_with_args = self.commands.get_nowait()
#                 command = command_with_args[0]
#                 args = command_with_args[1:]
#                 if command == 'create_board':
#                     self.command_create_board(*args)
#                 if command == 'reload_slave':
#                     slave_id, slave_name, slave_code = args
#                     self.command_reload_snake(slave_id, slave_name, slave_code)
#         except Queue.Empty:
#             pass


class RedisCommandThread(threading.Thread):
    def __init__(self, judge):
        threading.Thread.__init__(self)
        self.judge = judge

    def run(self):
        time.sleep(3)
        while True:
            # reload_slave;<slave_id>;<slave_name>;<slave_code>
            _, message = self.judge.r.blpop('commands')
            message = message.decode('utf-8')
            message = json.loads(message)
            self.judge.commands.put(message)


#SCRIPT = r"""
#import sys, random
#while True:
#    for x in range(60):
#        sys.stdin.readline()
#    sys.stdout.write(random.choice(['left', 'right', 'up', 'down']))
#    sys.stdout.write('\n')
#"""


# an explicit SIGTERM handler is needed when judge.py is the main
# docker container process...
def sigterm_handler(_signum, _frame):
    raise KeyboardInterrupt()


def main():
    # with open('keys', 'r') as keys_file:
    #     keys = keys_file.read().split("\n")
    # keys = [x.strip() for x in keys]
    # keys = [x for x in keys if x]

    judge = SnakeJudge(WIDTH, HEIGHT)
    random.seed()
    # for key in keys:
    #     judge.command_add_snake(key)

    print(judge.snakes.keys())

    thread = RedisCommandThread(judge)
    thread.daemon = True
    thread.start()

    signal.signal(signal.SIGTERM, sigterm_handler)

    judge.run()


if __name__ == '__main__':
    main()
