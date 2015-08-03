#!/usr/bin/env python
import json
import argparse
import time
from db import get_db


r = get_db()


def show_board(args):
  board = r.get('board')
  print board
  while args.repeat:
    time.sleep(0.5)
    board = r.get('board')
    print board


def snake_name(code):
    name = r.get('snake:%s:name' % code)
    if name is not None:
        return name.decode('utf-8')
    else:
        return u'Anonymous'


def players_func(args):
    codes = r.zrange('leaderboard', 0, -1, withscores=True)
    show_all = not(args.url or args.code or args.name or args.score)
    for (code, score) in codes:
        parts = []
        if args.url or show_all:
            parts.append(u"http://snakes.plocharz.info/snake/%s/" % code)
        if args.code or show_all:
            parts.append(code)
        if args.name or show_all:
            parts.append(snake_name(code))
        if args.score or show_all:
            parts.append(unicode(int(score)))
        print u"\t".join(parts).encode('utf-8')


def clear_program(args):
    if args.all:
        keys = r.smembers('keys')
    elif args.code:
        keys = [args.code]
    else:
        raise Exception("--code or --all required")
    keys = ['snake:%s:code' % key for key in keys]

    for key in keys:
        r.delete(key)
    reset(args)


def clear_leaderboard(args):
    print r.delete('leaderboard')


def reset(args):
    command = json.dumps((
        'reset',
    ))
    r.rpush('commands', command.encode('utf-8'))


def add_snake(args):
    command = json.dumps((
        'add_snake',
        args.key
    ))
    r.rpush('commands', command.encode('utf-8'))


def remove_snake(args):
    if args.all:
        keys = r.smembers('keys')
    elif args.key:
        keys = [args.key]
    else:
        raise Exception("snake key or --all is required")

    for key in keys:
        command = json.dumps((
            'remove_snake',
            key
        ))
        r.rpush('commands', command.encode('utf-8'))


parser = argparse.ArgumentParser()

subparsers = parser.add_subparsers()

players = subparsers.add_parser('clear_leaderboard')
players.set_defaults(func=clear_leaderboard)

players = subparsers.add_parser('clear_program')
players.add_argument('-a', "--all", action='store_true')
players.add_argument('-c', "--code")
players.set_defaults(func=clear_program)

players = subparsers.add_parser('players')
players.add_argument('-u', "--url", action='store_true')
players.add_argument('-c', "--code", action='store_true')
players.add_argument('-n', "--name", action='store_true')
players.add_argument('-s', "--score", action='store_true')
players.set_defaults(func=players_func)

reset_parser = subparsers.add_parser('reset')
reset_parser.set_defaults(func=reset)

add_snake_parser = subparsers.add_parser('add_snake')
add_snake_parser.add_argument('key', help='snake key')
add_snake_parser.set_defaults(func=add_snake)

remove_snake_parser = subparsers.add_parser('remove_snake')
remove_snake_parser.add_argument('-a', "--all", action='store_true')
remove_snake_parser.add_argument('key', help='snake key', nargs='?')
remove_snake_parser.set_defaults(func=remove_snake)

board = subparsers.add_parser('board')
board.add_argument('-r', '--repeat', action='store_true')
board.set_defaults(func=show_board)

parsed = parser.parse_args()
parsed.func(parsed)
