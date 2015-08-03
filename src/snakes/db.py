import redis


def get_db(id_=0):
    return redis.StrictRedis(host='localhost', port=6379, db=id_)
