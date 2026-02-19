import asyncio
import asyncpg

async def check_accounts():
    conn = await asyncpg.connect(
        host='finanza-bank.cluster-cxo2eume87bz.eu-north-1.rds.amazonaws.com',
        port=5432,
        user='postgres',
        password='Finanza123!',
        database='finanzadb'
    )
    
    # Check accounts for user 2 (test user)
    accounts = await conn.fetch(
        'SELECT id, account_number, account_type, balance FROM accounts WHERE owner_id = 2'
    )
    print(f"Accounts for user 2: {accounts}")
    
    await conn.close()

asyncio.run(check_accounts())
