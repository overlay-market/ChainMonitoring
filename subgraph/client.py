import requests

class ResourceClient:
    URL = 'https://api.studio.thegraph.com/proxy/49419/overlay-contracts/v0.0.8'
    PAGE_SIZE = 500

    def get_positions(self, timestamp_lower, timestamp_upper, page_size=PAGE_SIZE):
        all_positions = []
        query = f'''
        {{
            positions(where: {{ createdAtTimestamp_gt: { timestamp_lower }, createdAtTimestamp_lt: { timestamp_upper } }}, first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
                id
                createdAtTimestamp
                mint
                market {{
                    id
                }}
            }}
        }}
        '''
        response = requests.post(self.URL, json={'query': query})
        curr_positions = response.json().get('data', {}).get('positions', [])
        page_count = 0
        while len(curr_positions) > 0:
            page_count += 1
            print(f'Fetching page # {page_count}')
            all_positions.extend(curr_positions)
            query = f'''
            {{
                positions(where: {{ createdAtTimestamp_gt: {timestamp_lower}, createdAtTimestamp_lt: { int(curr_positions[-1]['createdAtTimestamp']) } }}, first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
                    id
                    createdAtTimestamp
                    mint
                    market {{
                        id
                    }}
                }}
            }}
            '''
            response = requests.post(self.URL, json={'query': query})
            curr_positions = response.json().get('data', {}).get('positions', [])
        
        return all_positions

    def get_mint_total_per_market(self, page_size = PAGE_SIZE):
        all_positions = []
        mint_total_per_market = {}
        query = f'''
        {{
            positions(first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
                id
                createdAtTimestamp
                mint
                market {{
                    id
                }}
            }}
        }}
        '''
        response = requests.post(self.URL, json={'query': query})
        curr_positions = response.json().get('data', {}).get('positions', [])
        # print('response', response.json())
        mint_total = 0
        while len(curr_positions) > 0:
            all_positions.extend(curr_positions)
            for position in curr_positions:
                if position['market']['id'] not in mint_total_per_market:
                    mint_total_per_market[position['market']['id']] = 0
                mint_total_per_market[position['market']['id']] += int(position['mint'])
                mint_total += int(position['mint'])

            query = f'''
            {{
                positions(where: {{ createdAtTimestamp_lt: { int(curr_positions[-1]['createdAtTimestamp']) } }}, first: {page_size}, orderBy: createdAtTimestamp, orderDirection: desc)  {{
                    id
                    createdAtTimestamp
                    mint
                    market {{
                        id
                    }}
                }}
            }}
            '''
            response = requests.post(self.URL, json={'query': query})
            curr_positions = response.json().get('data', {}).get('positions', [])

        # print('all_positions', all_positions)
        print('mint_total', mint_total)
        print('mint_total_per_market', mint_total_per_market)
        return mint_total, mint_total_per_market
