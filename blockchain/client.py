import math
import multiprocessing
import asyncio
import json
import time
from typing import List, Any

from concurrent.futures import ThreadPoolExecutor, as_completed
from web3.exceptions import ContractLogicError
from brownie import Contract, web3, network
from dank_mids.brownie_patch import patch_contract
from dank_mids.helpers import setup_dank_w3_from_sync
from datetime import datetime

from constants import CONTRACT_ADDRESS

MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 10  # Adjust delay as needed

def load_json_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            json_data = json.load(file)
        return json_data
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file {file_path}: {e}")
    except Exception as e:
        print(f"An error occurred while loading JSON from file {file_path}: {e}")


def get_value_of_position(contract, position, output_queue):
    try:
        pos_value = contract.value(position[0], position[1], position[2])
        output_queue.put(pos_value)
        return pos_value
    except ContractLogicError as e:
        print(e)
        return


class ResourceClient:
    def connect_to_network(self):
        print('Connecting to arbitrum network...')
        # network.connect('arbitrum-main')
        network.connect('Testnet')
        # network.connect('sepolia2')
        # network.connect('arbitrum-sepolia')
        print('Connected to arbitrum network...')
        print('Loading contract...')
        self.contract = self.load_contract(CONTRACT_ADDRESS)
        print('Contract loaded')


    def load_contract(self, address: str) -> Contract:
        """
        Load a contract using the provided address.

        Args:
            address (str): The Ethereum address of the contract.

        Returns:
            Contract: An instance of the loaded contract.

        This function attempts to load the contract directly from memory. If that fails, it fetches it from the explorer
        the first time the script is run. It then sets up the contract with a patched web3 instance and returns the
        resulting contract.

        Args Details:
            - `address`: The Ethereum address of the contract.

        Note:
            - `Contract`, `setup_dank_w3_from_sync`, and `patch_contract` are assumed to be defined functions.
            - `web3` is assumed to be a global object representing the Ethereum web3 instance.
        """
        # try:
        #     # Loads faster from memory
        #     contract = Contract(address)
        # except ValueError:
        # Loads from explorer first time script is run
        # contract = Contract.from_explorer(address)
        print('Loading contract from abi...')
        abi = load_json_from_file('././periphery_abi.json')
        print('abi loaded!', abi)
        contract = Contract.from_abi(name='contract', address=address, abi=abi)
        # dank_w3 = setup_dank_w3_from_sync(web3)
        # dank_contract = patch_contract(contract, dank_w3)
        return contract

    def get_position_value(self, pos: tuple) -> Any:
        """
        Asynchronously retrieve the value of a position from the contract.

        Args:
            contract: The contract object providing access to position values.
            pos (tuple): A tuple containing the position information (market ID, position ID, user address).

        Returns:
            Any: The value of the position, or None if an error occurs.

        This asynchronous function attempts to retrieve the value of a position from the contract. If successful, it returns
        the value. If a ContractLogicError is raised, it prints the error message and returns None.

        Args Details:
            - `contract`: The contract object providing access to position values.
            - `pos`: A tuple containing the position information (market ID, position ID, user address).

        Note:
            - `ContractLogicError` is assumed to be defined.
            - The `contract.value.coroutine` method is assumed to be an asynchronous method for fetching position values.

        """
        try:
            pos_value = self.contract.value(pos[0], pos[1], pos[2])
            print(f'Starting execution for pos {pos}', datetime.now())
            print('pos_value', pos_value)
            print(f'Function executed! {pos}', datetime.now())
            return pos_value
        except ContractLogicError as e:
            print(e)
            return
    
    # async def get_position_value(self, pos):
    #     print(f'Starting execution {pos}', datetime.now())
    #     await asyncio.sleep(5)
    #     print(f'Function executed! {pos}', datetime.now())
    #     return pos*2

    async def get_value_of_positions(self, positions: List) -> List:
        """
        Get the current value of a list of positions.

        Args:
            positions (List): A list of positions to retrieve values for.

        Returns:
            List: A list of values corresponding to the provided positions.

        Raises:
            Any exceptions raised during the asynchronous gathering of position values.

        Example:
            positions = [...]  # List of positions
            values = await get_value_of_positions(positions)
        """
        values = []
        batch_size = 100
        # Get current value of live positions by batches
        for i in range(math.ceil(len(positions) / batch_size)):
            index_lower = i * batch_size
            index_upper = (i + 1) * batch_size
            print(f'[upnl] fetching values for batch {index_upper} out of {len(positions)}...')
            if index_upper > len(positions):
                index_upper = len(positions)
            curr_post_list = positions[index_lower:index_upper]
            values.extend(
                await asyncio.gather(*[self.get_position_value(pos) for pos in curr_post_list])
            )
            # await asyncio.sleep(5)
        return values

    # def process_positions(self, positions):
    #     with ThreadPoolExecutor() as executor:
    #         futures = {executor.submit(self.get_position_value, pos): pos for pos in positions}
    #         for future in as_completed(futures):
    #             pos = futures[future]
    #             try:
    #                 result = future.result()
    #                 print(f"Position value for {pos}: {result}")
    #             except Exception as e:
    #                 print(f"Error processing position {pos}: {e}")
    
    # def process_positions(self, positions):
    #     with ThreadPoolExecutor() as executor:
    #         futures = {executor.submit(self.get_position_value, pos): pos for pos in positions}
    #         results = []
    #         for future in as_completed(futures):
    #             pos = futures[future]
    #             try:
    #                 result = future.result()
    #                 results.append((pos, result))
    #             except Exception as e:
    #                 results.append((pos, None))
    #                 print(f"Error processing position {pos}: {e}")
    #     return results

    def retry_get_position_value(self, pos: tuple):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                pos_value = self.contract.value(pos[0], pos[1], pos[2])
                print(f'Starting execution for pos {pos}', datetime.now())
                print('pos_value', pos_value)
                print(f'Function executed! {pos}', datetime.now())
                return pos_value
            except Exception as e:
                print(f"Error processing position {pos}: {e}. Retrying...")
                retries += 1
                time.sleep(RETRY_DELAY_SECONDS)
        return None

    def process_positions(self, positions):
        with ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.get_position_value, pos): pos for pos in positions}
            results = []
            for future in as_completed(futures):
                pos = futures[future]
                try:
                    result = future.result()
                    if result is not None:
                        results.append((pos, result))
                except Exception as e:
                    print(f"Error processing position {pos}: {e}. Retrying...")
                    result = self.retry_get_position_value(pos)
                    if result is not None:
                        results.append((pos, result))
                    else:
                        print(f"Max retries reached for position {pos}. Giving up.")
        return results
