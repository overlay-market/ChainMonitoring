import json
import pandas as pd
import requests
from pydantic import ValidationError
from typing import List, Dict, Union

from constants import SUBGRAPH_API_KEY
from .models import Position, Build


MODEL_MAP = {
    'positions': Position,
    'builds': Build,
}


def extract_live_positions(builds: List[Dict]):
    builds_df = pd.json_normalize(builds)
    # Get market contract address and position id in separate columns
    builds_df[['market', 'position_id']] = builds_df['id'].str.split('-', expand=True)
    builds_df['position_id'] = builds_df['position_id'].apply(lambda x: int(x, 16))

    # Types and make readable
    builds_df['collateral'] = builds_df['collateral'].astype(float)/1e18
    builds_df['position.fractionUnwound'] = builds_df['position.fractionUnwound'].astype(float)/1e18
    builds_df['position.currentOi'] = builds_df['position.currentOi'].astype(float)/1e18

    # Adjust collateral based on position unwound
    builds_df['collateral_rem'] = builds_df['collateral'] * (1 - builds_df['position.fractionUnwound'])
    builds_df = builds_df[builds_df['position.currentOi'] > 0]
    # live_positions = builds_df[['market', 'owner.id', 'position_id', 'collateral_rem']].values.tolist()
    live_positions = builds_df.to_dict(orient='records')
    return live_positions


class ResourceClient:
    # URL = 'https://api.studio.thegraph.com/proxy/49419/overlay-contracts/v0.0.8'
    # URL = 'https://api.studio.thegraph.com/query/46086/overlay-v2-subgraph-arbitrum/version/latest'
    # URL = 'https://api.studio.thegraph.com/query/50057/overlay-arbitrum/v1.0.1'
    URL = f'https://gateway-arbitrum.network.thegraph.com/api/{SUBGRAPH_API_KEY}/subgraphs/id/7RuVCeRzAHL5apu6SWHyUEVt3Ko2pUv2wMTiHQJaiUW9'
    PAGE_SIZE = 500

    @staticmethod
    def validate_response(
        response: requests.Response, list_key: str
    ) -> List[Dict[str, Union[str, int, float]]]:
        """
        Validate the response from a subgraph API.

        Args:
            response (requests.Response): The HTTP response object.
            list_key (str): The key for the list in the response JSON.

        Returns:
            list: A list of validated records.

        Raises:
            Exception: If there are errors in the subgraph API response or if the response data is empty.
            ValidationError: If there is a validation error while processing the records.

        Example:
            response = requests.get(subgraph_url)
            validated_records = validate_response(response, "positions")
        """
        response_json = response.json()
        errors = response_json.get('errors')
        data = response_json.get('data')
        if errors:
            raise Exception('Got errors from subgraph api response:', errors)
        if not data:
            raise Exception('Subgraph API returned empty data')
        model = MODEL_MAP[list_key]
        record_list = data.get(list_key)
        try:
            for item in record_list:
                model(**item)
        except ValidationError as e:
            print('ValidationError', e)
            raise e
        return record_list
    
    @staticmethod
    def build_query(
        list_key: str,
        where: Dict,
        filters: Dict,
        includes: List[str],
        nested_includes: Dict
    ) -> str:
        """
        Build a GraphQL query string.

        Args:
            list_key (str): The key for the list to query.
            where (Dict): A dictionary representing the 'where' condition.
            filters (Dict): A dictionary representing filters.
            includes (List[str]): A list of strings to include in the query.
            nested_includes (Dict): A dictionary of nested includes.

        Returns:
            str: The generated GraphQL query string.

        Example:
            query = build_query(
                list_key="positions",
                where={"name": "John Doe"},
                filters={"active": True},
                includes=["name", "email"],
                nested_includes={"profile": ["age", "location"]}
            )
        """
        where_string = json.dumps(where).replace('"', '')
        filters_string = json.dumps(filters).replace('"', '').replace('{', '').replace('}', '')
        includes_string = '\n'.join(includes)
        nested_includes_string = ''
        for key, value in nested_includes.items():
            attrs_string = '\n'.join(value)
            nested_includes_string += f'''
                {key} {{
                    {attrs_string}
                }}
            '''
        query = f'''
        {{
            {list_key}(where: {where_string}, {filters_string}) {{
                {includes_string}
                {nested_includes_string}
            }}
        }}
        '''
        return query
    
    def build_query_for_positions(
        self, where: Dict, page_size: int
    ) -> str:
        query = self.build_query(
            'positions',
            where=where,
            filters={
                'first': page_size,
                'orderBy': 'createdAtTimestamp',
                'orderDirection': 'desc'
            },
            includes=['id', 'createdAtTimestamp', 'mint'],
            nested_includes={ 'market': ['id'] }
        )
        return query

    def build_query_for_builds(
        self, where: Dict, page_size: int
    ) -> str:
        query = self.build_query(
            'builds',
            where=where,
            filters={
                'first': page_size,
                'orderBy': 'timestamp',
                'orderDirection': 'desc'
            },
            includes=['timestamp', 'collateral', 'id'],
            nested_includes={
                'position': ['currentOi', 'fractionUnwound'],
                'owner': ['id']
            }
        )
        return query

    from typing import List, Dict, Union

    def get_positions(
        self, timestamp_lower: int, timestamp_upper: int, page_size: int = PAGE_SIZE
    ) -> List[Dict[str, Union[int, float, str]]]:
        all_positions: List[Dict[str, Union[int, float, str]]] = []
        query: str = self.build_query_for_positions(
                where={
                'createdAtTimestamp_gt': timestamp_lower,
                'createdAtTimestamp_lt': timestamp_upper
            },
            page_size=page_size
        )
        response: requests.Response = requests.post(self.URL, json={'query': query})
        curr_positions: List[Dict[str, Union[int, float, str]]] = self.validate_response(response, 'positions')
        page_count: int = 0
        while len(curr_positions) > 0:
            page_count += 1
            print(f'Fetching positions page # {page_count}')
            all_positions.extend(curr_positions)
            query = self.build_query_for_positions(
                where={ 
                    'createdAtTimestamp_gt': timestamp_lower,
                    'createdAtTimestamp_lt': int(curr_positions[-1]['createdAtTimestamp'])
                },
                page_size=page_size
            )
            response = requests.post(self.URL, json={'query': query})
            curr_positions = self.validate_response(response, 'positions')
        
        return all_positions

    def get_all_positions(
        self, page_size: int = PAGE_SIZE
    ) -> List[Dict[str, Union[int, float, str]]]:
        all_positions: List[Dict[str, Union[int, float, str]]] = []
        query: str = self.build_query_for_positions(where={}, page_size=page_size)
        response: requests.Response = requests.post(self.URL, json={'query': query})
        curr_positions: List[Dict[str, Union[int, float, str]]] = self.validate_response(response, 'positions')
        while len(curr_positions) > 0:
            all_positions.extend(curr_positions)
            query = self.build_query_for_positions(
                where={
                    'createdAtTimestamp_lt': int(curr_positions[-1]['createdAtTimestamp'])
                },
                page_size=page_size
            )
            response = requests.post(self.URL, json={'query': query})
            curr_positions = self.validate_response(response, 'positions')

        print('all_positions', len(all_positions))
        return all_positions

    def get_all_live_positions(
        self, page_size: int = PAGE_SIZE
    ) -> List[Dict[str, Union[int, float, str]]]:
        live_positions: List[Dict[str, Union[int, float, str]]] = []
        query: str = self.build_query_for_builds(where={}, page_size=page_size)
        response: requests.Response = requests.post(self.URL, json={'query': query})
        curr_builds: List[Dict[str, Union[int, float, str]]] = self.validate_response(response, 'builds')
        curr_live_positions: List[Dict[str, Union[int, float, str]]] = extract_live_positions(curr_builds)
        page_count: int = 0
        while True:
            page_count += 1
            print(f'Fetching builds page # {page_count}')
            live_positions.extend(curr_live_positions)
            query = self.build_query_for_builds(
                where={
                    'timestamp_lt': int(curr_builds[-1]['timestamp'])
                },
                page_size=page_size
            )
            response = requests.post(self.URL, json={'query': query})
            curr_builds = self.validate_response(response, 'builds')

            if len(curr_builds) == 0:
                break

            curr_live_positions = extract_live_positions(curr_builds)
        return live_positions
