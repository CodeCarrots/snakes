import os
import redis

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

def get_db(id_=0):
    return redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=id_)
