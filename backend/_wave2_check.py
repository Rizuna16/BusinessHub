import asyncio, asyncpg

async def check():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/businesshub_validation')
    rev = await conn.fetchval('SELECT version_num FROM alembic_version')
    print('Current revision:', rev)
    idxs = await conn.fetch("SELECT indexname, indexdef FROM pg_indexes WHERE indexname LIKE 'uq_%' ORDER BY indexname")
    for r in idxs:
        print(f"  {r['indexname']}: unique={'UNIQUE' in r['indexdef']}")
    await conn.close()

asyncio.run(check())
