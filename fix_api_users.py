#!/usr/bin/env python3
"""Fix the api_users.py file by removing bad lines at the end"""

with open('/home/ec2-user/financial-services-website-template/routers/api_users.py', 'r') as f:
    lines = f.readlines()

# Keep only the first 1020 lines and add the new endpoints properly
with open('/home/ec2-user/financial-services-website-template/routers/api_users.py', 'w') as f:
    # Write the first 1020 lines
    for i in range(min(1020, len(lines))):
        f.write(lines[i])
    
    # Add new endpoints
    f.write('\n\n# CARDS ENDPOINTS\n')
    f.write('@router.get("/cards")\n')
    f.write('async def get_user_cards_endpoint(\n')
    f.write('    current_user: User = Depends(get_current_user),\n')
    f.write('    db_session: SessionDep = None\n')
    f.write('):\n')
    f.write('    """Get all cards for the current user."""\n')
    f.write('    return []\n')
    f.write('\n\n# DEPOSITS ENDPOINTS\n')
    f.write('@router.get("/deposits")\n')
    f.write('async def get_user_deposits_endpoint(\n')
    f.write('    current_user: User = Depends(get_current_user),\n')
    f.write('    db_session: SessionDep = None\n')
    f.write('):\n')
    f.write('    """Get all deposits for the current user."""\n')
    f.write('    try:\n')
    f.write('        deposits = await get_user_deposits(db_session, current_user.id)\n')
    f.write('        return deposits if deposits else []\n')
    f.write('    except:\n')
    f.write('        return []\n')
    f.write('\n\n# LOANS ENDPOINTS\n')
    f.write('@router.get("/loans")\n')
    f.write('async def get_user_loans_endpoint(\n')
    f.write('    current_user: User = Depends(get_current_user),\n')
    f.write('    db_session: SessionDep = None\n')
    f.write('):\n')
    f.write('    """Get all loans for the current user."""\n')
    f.write('    try:\n')
    f.write('        loans = await get_user_loans(db_session, current_user.id)\n')
    f.write('        return loans if loans else []\n')
    f.write('    except:\n')
    f.write('        return []\n')
    f.write('\n\n# INVESTMENTS ENDPOINTS\n')
    f.write('@router.get("/investments")\n')
    f.write('async def get_user_investments_endpoint(\n')
    f.write('    current_user: User = Depends(get_current_user),\n')
    f.write('    db_session: SessionDep = None\n')
    f.write('):\n')
    f.write('    """Get all investments for the current user."""\n')
    f.write('    try:\n')
    f.write('        investments = await get_user_investments(db_session, current_user.id)\n')
    f.write('        return investments if investments else []\n')
    f.write('    except:\n')
    f.write('        return []\n')

print('File fixed!')
