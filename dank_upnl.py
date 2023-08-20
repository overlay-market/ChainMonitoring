import requests
import pandas as pd
import asyncio

import brownie
brownie.network.connect('arbitrum-main')
from brownie import Contract, web3
from dank_mids.brownie_patch import patch_contract
from dank_mids.helpers import setup_dank_w3_from_sync

# Dank mids setup
dank_w3 = setup_dank_w3_from_sync(web3)

# Contract addresses
STATE = '0xC3cB99652111e7828f38544E3e94c714D8F9a51a'

SUBGRAPH_URL = 'https://api.studio.thegraph.com/proxy/49419/overlay-contracts/v0.0.7'


# Query for mint events
def query():
    query = '''
    {
        builds {
            collateral
            id
            position {
                currentOi
                fractionUnwound
            }
            owner {
                id
            }
        }
    }
    '''
    # Get result in pandas df
    response = requests.post(SUBGRAPH_URL, json={'query': query})
    result = response.json().get('data', {}).get('builds', [])
    df = pd.json_normalize(result)

    # Get market contract address and position id in separate columns
    df[['market', 'position_id']] = df['id'].str.split('-', expand=True)
    df['position_id'] = df['position_id'].apply(lambda x: int(x, 16))

    # Types and make readable
    df['collateral'] = df['collateral'].astype(float)/1e18
    df['position.fractionUnwound'] = df['position.fractionUnwound'].astype(float)/1e18
    df['position.currentOi'] = df['position.currentOi'].astype(float)/1e18

    # Adjust collateral based on position unwound
    df['collateral_rem'] = df['collateral'] * (1 - df['position.fractionUnwound'])

    return df


def live_positions(df):
    df = df[df['position.currentOi'] > 0]
    return df


def load_contract(address):
    try:
        # Loads faster from memory
        contract = Contract(address)
    except ValueError:
        # Loads from explorer first time script is run
        contract = Contract.from_explorer(address)
    dank_contract = patch_contract(contract, dank_w3)
    return dank_contract


async def get_pos_value(state, pos):
    return await state.value.coroutine(pos[0], pos[1], pos[2])


def get_pos_list(df):
    result = df[['market', 'owner.id', 'position_id']].values.tolist()
    return result


async def _main():
    df = query()
    print(f'Original df shape: {df.shape}')
    df = live_positions(df)
    print(f'Pruned df shape: {df.shape}')

    state = load_contract(STATE)
    pos_list = get_pos_list(df)
    values = await asyncio.gather(*[get_pos_value(state, pos) for pos in pos_list])
    values = [v/1e18 for v in values]
    df['value'] = values
    df['upnl'] = df['value'] - df['collateral_rem']
    df['upnl_pct'] = df['upnl'] / df['collateral_rem']


if __name__ == "__main__":
    asyncio.run(_main())
