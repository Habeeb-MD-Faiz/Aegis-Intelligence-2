"""
Check that on-chain anchoring will actually work, without spending anything.

    python anchor_preflight.py

Everything about anchoring is unit-tested offline (see test_anchor.py) except
the one thing that needs a real network and a funded account: whether Base
Sepolia accepts the transaction. Run this before relying on anchoring in a
demo, rather than discovering at block 5 that the account is empty.

Reads your key, derives the address, and queries balance, gas price and nonce.
It never broadcasts.
"""

import sys

import anchor
import config


def main() -> int:
    print("\nAEGIS — anchoring preflight")
    print("=" * 46)
    print(f"  chain     {config.CHAIN_NAME} (id {anchor.BASE_SEPOLIA_CHAIN_ID})")
    print(f"  rpc       {config.CHAIN_RPC_URL}")
    print(f"  every     {config.ANCHOR_EVERY} blocks")
    print()

    result = anchor.preflight()

    if not result["ready"]:
        print(f"  ✗ NOT READY — {result['reason']}")

        if "address" in result:
            print(f"    address   {result['address']}")
            print(f"    balance   {result.get('balanceWei', 0) / 1e18:.6f} ETH")
            print(f"    needed    ~{result.get('estimatedCostWei', 0) / 1e18:.6f} ETH")
            print()
            print("    Fund it from a Base Sepolia faucet, then re-run.")

        print()
        print("  Anchoring is optional. Without it the ledger is still")
        print("  hash-linked and tamper-evident locally — just not anchored.")
        print()

        return 1

    print("  ✓ READY")
    print(f"    address   {result['address']}")
    print(f"    balance   {result['balanceWei'] / 1e18:.6f} ETH")
    print(f"    cost/anchor ~{result['estimatedCostWei'] / 1e18:.8f} ETH")
    print(f"    nonce     {result['nonce']}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
