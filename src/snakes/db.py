import redis


def get_db():
    return redis.StrictRedis(host='localhost', port=6379, db=0)