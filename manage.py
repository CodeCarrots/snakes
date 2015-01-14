#!/usr/bin/env python
import json
import argparse
from db import get_db


r = get_db()


def snake_name(code):
    name = r.get('snake:%s:name' % code)
    if name is not None:
        return name.decode('utf-8')
    else:
        return u'Anonymous'


def players_func(args):
    codes = r.zrange('leaderboard', 0, -1, withscores=True)
    for (code, score) in codes:
        parts = []
        if args.url:
            parts.append(u"http://snakes.plocharz.info/snake/%s/" % code)
        if args.code:
            parts.append(code)
        if args.name:
            parts.append(snake_name(code))
        if args.score:
            parts.append(unicode(int(score)))
        print u"\t".join(parts).encode('utf-8')


def clear_program(args):
    if args.all:
        keys = r.keys('snake:*:code')
    else:
        keys = ['snake:%s:code' % args.code]
    
    for key in keys:
        print r.delete(key)


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
    command = json.dumps((
        'remove_snake',
        args.key
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
remove_snake_parser.add_argument('key', help='snake key')
remove_snake_parser.set_defaults(func=remove_snake)

parsed = parser.parse_args()
parsed.func(parsed)
