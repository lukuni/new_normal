"""Publish the latest ledger Merkle root to ProposalRegistry on an EVM chain (e.g. Sepolia).

    pip install web3==7.6.0 requests
    export API_URL=http://localhost:8000 ADMIN_TOKEN=... RPC_URL=https://sepolia.infura.io/v3/<key>
    export PRIVATE_KEY=0x... CONTRACT_ADDRESS=0x...
    python scripts/anchor_onchain.py

Steps: POST /api/anchors (backend computes the Merkle root of new blocks) ->
send anchor(root, from, to) transaction -> PATCH /api/anchors/{id} with the tx hash.
Note: requires a funded test-network wallet; not exercised in automated tests.
"""
import json
import os
import pathlib
import sys

import requests
from web3 import Web3

API = os.environ.get("API_URL", "http://localhost:8000")
HDR = {"X-Admin-Token": os.environ["ADMIN_TOKEN"]}
ABI = json.loads((pathlib.Path(__file__).parent.parent / "contracts" / "ProposalRegistry.abi.json").read_text())


def main() -> int:
    r = requests.post(f"{API}/api/anchors", headers=HDR, timeout=30)
    if r.status_code == 409:
        print("No new blocks to anchor.")
        return 0
    r.raise_for_status()
    a = r.json()
    print(f"Anchor #{a['id']}: blocks {a['from_index']}-{a['to_index']} root {a['merkle_root']}")

    w3 = Web3(Web3.HTTPProvider(os.environ["RPC_URL"]))
    acct = w3.eth.account.from_key(os.environ["PRIVATE_KEY"])
    c = w3.eth.contract(address=Web3.to_checksum_address(os.environ["CONTRACT_ADDRESS"]), abi=ABI)
    tx = c.functions.anchor(bytes.fromhex(a["merkle_root"]), a["from_index"], a["to_index"]).build_transaction({
        "from": acct.address, "nonce": w3.eth.get_transaction_count(acct.address)})
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction).hex()
    w3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
    requests.patch(f"{API}/api/anchors/{a['id']}", headers=HDR,
                   params={"tx_hash": tx_hash, "network": os.environ.get("NETWORK", "sepolia")}, timeout=30).raise_for_status()
    print("Published:", tx_hash)
    return 0


if __name__ == "__main__":
    sys.exit(main())
