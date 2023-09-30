import math
import asyncio
from typing import List, Any

from web3.exceptions import ContractLogicError
from brownie import Contract, web3, network
from dank_mids.brownie_patch import patch_contract
from dank_mids.helpers import setup_dank_w3_from_sync

from constants import CONTRACT_ADDRESS


class ResourceClient:
    def connect_to_network(self):
        print('Connecting to arbitrum network...')
        network.connect('arbitrum-main')
        self.contract = self.load_contract(CONTRACT_ADDRESS)

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
        try:
            # Loads faster from memory
            contract = Contract(address)
        except ValueError:
            # Loads from explorer first time script is run
            contract = Contract.from_explorer(address)
        dank_w3 = setup_dank_w3_from_sync(web3)
        dank_contract = patch_contract(contract, dank_w3)
        return dank_contract

    async def get_position_value(self, pos: tuple) -> Any:
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
            pos_value = await self.contract.value.coroutine(pos[0], pos[1], pos[2])
            return pos_value
        except ContractLogicError as e:
            print(e)
            return
    
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
        batch_size = 50
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
            await asyncio.sleep(5)
        return values
