from functions.mint import MintMonitoringHandler
handler = MintMonitoringHandler()
handler.calculate_metrics()
metrics = handler.calculate_metrics()
# [{'name': 'ovl_token_minted', 'value': {'ALL': -805.7973282971279, 'LINK / USD': -94.96272053405455, 'SOL / USD': -167.26353028247604, 'APE / USD': -69.12437849497073, 'Crypto Volatility Index': 240.00793524473616, 'AVAX / USD': -84.59636423287223, 'MATIC / USD': -100.97709948693603, 'WBTC / USD': -528.8811705105545}}]