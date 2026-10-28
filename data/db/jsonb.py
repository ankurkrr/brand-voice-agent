from asyncpg.pgproto import pgproto

def to_jsonb(data):
    return pgproto.Jsonb(data)
