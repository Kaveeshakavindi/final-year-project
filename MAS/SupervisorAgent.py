import asyncio
import json

from typing import Dict, List, Any, Optional
from dataclasses import  asdict
from enum import Enum

import time
from taskStatus import TaskStatus
from task import Task
from logger import logger
from ollamaClient import OllamaClient
from ABIs.esgAbi import ESG_ABI


from web3 import Web3

class SupervisorAgent:
    def __init__(self, ollama_url: str = "http://localhost:11434", rpc_url: str = "http://127.0.0.1:8545"):
        self.ollama = OllamaClient(ollama_url)
        self.tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.max_concurrent_tasks = 3

        # connect to Ganache or Ethereum node
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.web3.is_connected():
            raise Exception("Web3 not connected! Check RPC URL.")

        # registry of "contracts"
        self.contracts = {
            "esgdata": self._execute_esgdata_contract  # new
        }

    # -------------------------
    # ESG Contract Interaction
    # -------------------------
    async def _execute_esgdata_contract(self, prompt: str, model: str):
        """
        Example: prompt contains ESG submission data in JSON format
        {
            "companyId": "121",
            "reportingPeriod": "Q1-2025",
            "kpiType": "POLLUTANTS_EMMISSION",
            "value": "320",
            "dataHash": "QmHash12345"
        }
        """
        try:
            data = json.loads(prompt)

          
            

            # replace with actual deployed address from Truffle
            contract_address = "0x694eAeEdbF24A21Dd76698edc7eB2CfC13e867CA"
            contract = self.web3.eth.contract(address=contract_address, abi=ESG_ABI)

            # select account to send tx
            acct = self.web3.eth.accounts[0]

            # build and send transaction
            tx_hash = contract.functions.submitESGData(
                data["companyId"],
                data["reportingPeriod"],
                data["kpiType"],
                data["value"],
                data["dataHash"]
            ).transact({"from": acct})

            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            return {
                "status": "submitted",
                "txHash": tx_hash.hex(),
                "blockNumber": receipt.blockNumber
            }

        except Exception as e:
            return {"error": str(e)}
