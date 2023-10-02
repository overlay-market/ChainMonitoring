import os

MAP_MARKET_ID_TO_NAME = {
    "0x02e5938904014901c96f534b063ec732ea3b48d5": "LINK / USD",
    "0x1067b7df86552a53d816ce3fed50d6d01310b48f": "SOL / USD",
    "0x33659282d39e62b62060c3f9fb2230e97db15f1e": "APE / USD",
    "0x35e1d28ad9d8a80cff5bbf163a735c54eb6c1342": "AZUKI / WETH",
    "0x5114215415ee91ab5d973ba62fa9153ece1f6c5a": "NFT Blue Chip Index / USD",
    "0x7c65c99ba1edfc94c535b7aa2d72b0f7357a676b": "Crypto Volatility Index",
    "0x833ba1a942dc6d33bc3e6959637ae00e0cdcb20b": "AVAX / USD",
    "0x8440e56c2675d9b8e04183da3a3a744a4a16ed33": "Memecoins Index",
    "0x8c7dc90243fc7984583339da8df0a5d57ec491db": "PUDGIES / WETH",
    "0x8c82c349e349ffd9403c3984cb1ad1b0f76f7d2e": "PUNKS / WETH",
    "0x909d893d5e7f250659fa56c2ca2920760eebb17f": "BAYC / WETH",
    "0xa811698d855153cc7472d1fb356149a94bd618e7": "MATIC / USD",
    "0xb31d222c23104cbc2c04df77941f1f2c478133dd": "BAYC / WETH",
    "0xc28350047d006ed387b0f210d4ea3218137a8a38": "WBTC / USD",
    "0xccd645835ca0033f0c1106e7b24f288e59e867e8": "MILADY / WETH",
    "0xce45c64911bd0a088daabd73ee1bc09ae98cd84b": "MAYC / WETH",
    "0xf30c5cb6205f115799b275430ea0874359476304": "Total Crypto Market Cap / USD",
}

AVAILABLE_MARKETS = [
  '0x02e5938904014901c96f534b063ec732ea3b48d5',
  '0x1067b7df86552a53d816ce3fed50d6d01310b48f',
  '0x33659282d39e62b62060c3f9fb2230e97db15f1e',
  # '0x35e1d28ad9d8a80cff5bbf163a735c54eb6c1342', # 'AZUKI / WETH'
  # '0x5114215415ee91ab5d973ba62fa9153ece1f6c5a',
  '0x7c65c99ba1edfc94c535b7aa2d72b0f7357a676b',
  '0x833ba1a942dc6d33bc3e6959637ae00e0cdcb20b',
  # '0x8c7dc90243fc7984583339da8df0a5d57ec491db', # 'PUDGIES / WETH'
  # '0x8c82c349e349ffd9403c3984cb1ad1b0f76f7d2e', # 'PUNKS / WETH'
  '0xa811698d855153cc7472d1fb356149a94bd618e7',
  # '0xb31d222c23104cbc2c04df77941f1f2c478133dd', # 'BAYC / WETH'
  '0xc28350047d006ed387b0f210d4ea3218137a8a38',
  # '0xccd645835ca0033f0c1106e7b24f288e59e867e8', # 'MILADY / WETH'
  # '0xce45c64911bd0a088daabd73ee1bc09ae98cd84b', # 'MAYC / WETH'
  # '0xF30C5cB6205f115799b275430Ea0874359476304'.toLowerCase(), # Total Crypto Market Cap
  # '0x8440E56C2675d9b8E04183dA3a3a744a4a16ED33'.toLowerCase(), # memecoins
]

ALL_MARKET_LABEL = 'ALL'

QUERY_INTERVAL = 60
MINT_DIVISOR = 10 ** 18

SUBGRAPH_API_KEY = os.environ.get("SUBGRAPH_API_KEY")

# Contract addresses
CONTRACT_ADDRESS = '0xC3cB99652111e7828f38544E3e94c714D8F9a51a'
