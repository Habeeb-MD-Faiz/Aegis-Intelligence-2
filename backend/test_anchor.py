"""
Anchoring tests.

The anchoring code previously existed but had never executed once — it only
ran when a funded key was configured, so its riskiest parts (transaction
construction, the eth-account raw-transaction rename, hex encoding) were
entirely unexercised.

These tests run the whole path with a real throwaway key and a fake JSON-RPC
endpoint. Everything is proven except the final network broadcast:

  PROVEN HERE   payload encoding and decoding, gas estimation, transaction
                construction, signing, signature recovery, raw hex encoding,
                the RPC request/response contract, nonce and gas-price
                handling, failure isolation, preflight.

  NOT PROVEN    that Base Sepolia accepts the transaction. That needs a funded
                account and a real network. Run `python -m anchor_preflight`
                against your key before relying on it.
"""

import json
import os
from typing import Dict, List

os.environ.setdefault("AEGIS_DB_FILE", "/tmp/aegis-anchor-test.db")
os.environ.setdefault("AEGIS_LEDGER_FILE", "/tmp/aegis-anchor-test.json")
os.environ.setdefault("AEGIS_SEED_DEMO_DATA", "false")

import pytest  # noqa: E402
from eth_account import Account  # noqa: E402

import anchor  # noqa: E402
import config  # noqa: E402


# A throwaway key generated for tests. Never funded, never used anywhere else.
TEST_ACCOUNT = Account.from_key(
    "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
)

CHAIN_HEAD = "a3f1" + "0" * 60


@pytest.fixture(autouse=True)
def clean():
    anchor.reset()
    yield
    anchor.reset()


class FakeRpc:
    """
    A stand-in JSON-RPC endpoint that records what it was asked.
    """

    def __init__(self, **overrides):
        self.calls: List[Dict] = []
        self.responses = {
            "eth_getTransactionCount": "0x7",
            "eth_gasPrice": "0x3b9aca00",  # 1 gwei
            "eth_getBalance": hex(10**18),
            "eth_sendRawTransaction": "0x" + "ab" * 32,
            **overrides,
        }

    def __call__(self, method: str, params: list) -> str:
        self.calls.append({"method": method, "params": params})

        if method not in self.responses:
            raise RuntimeError(f"unexpected method {method}")

        result = self.responses[method]

        if isinstance(result, Exception):
            raise result

        return result

    def method_names(self) -> List[str]:
        return [call["method"] for call in self.calls]


# ============================================================
# PAYLOAD
# ============================================================

def test_payload_roundtrips():
    payload = anchor.build_payload(42, CHAIN_HEAD)
    decoded = anchor.decode_payload("0x" + payload.hex())

    assert decoded == {"aegis": "ledger-anchor", "block": 42, "head": CHAIN_HEAD}


def test_payload_is_deterministic():
    assert anchor.build_payload(1, CHAIN_HEAD) == anchor.build_payload(1, CHAIN_HEAD)


def test_decode_rejects_foreign_calldata():
    assert anchor.decode_payload("0xdeadbeef") is None
    assert anchor.decode_payload("0x" + json.dumps({"x": 1}).encode().hex()) is None


def test_gas_scales_with_payload():
    small = anchor.estimate_gas(b"x")
    large = anchor.estimate_gas(b"x" * 500)

    assert large > small >= anchor.BASE_GAS


# ============================================================
# TRANSACTION CONSTRUCTION
# ============================================================

def test_transaction_is_zero_value_and_self_addressed():
    tx = anchor.build_transaction(
        address=TEST_ACCOUNT.address,
        nonce=7,
        gas_price=10**9,
        block_number=42,
        chain_head=CHAIN_HEAD,
    )

    assert tx["value"] == 0, "an anchor must never transfer value"
    assert tx["to"] == TEST_ACCOUNT.address
    assert tx["chainId"] == anchor.BASE_SEPOLIA_CHAIN_ID == 84532
    assert tx["nonce"] == 7


def test_transaction_carries_the_chain_head():
    tx = anchor.build_transaction(
        TEST_ACCOUNT.address, 0, 10**9, 99, CHAIN_HEAD
    )

    assert anchor.decode_payload(tx["data"])["head"] == CHAIN_HEAD


def test_gas_covers_the_calldata():
    tx = anchor.build_transaction(
        TEST_ACCOUNT.address, 0, 10**9, 1, CHAIN_HEAD
    )

    calldata_bytes = len(tx["data"][2:]) // 2
    minimum = anchor.BASE_GAS + calldata_bytes * anchor.GAS_PER_CALLDATA_BYTE

    assert tx["gas"] >= minimum


# ============================================================
# SIGNING — the part that was never exercised
# ============================================================

def test_signing_produces_broadcastable_hex():
    tx = anchor.build_transaction(
        TEST_ACCOUNT.address, 0, 10**9, 1, CHAIN_HEAD
    )

    raw = anchor.sign_transaction(tx, TEST_ACCOUNT.key)

    assert raw.startswith("0x")
    assert len(raw) > 100
    bytes.fromhex(raw[2:])  # must be valid hex


def test_signature_recovers_to_the_signing_account():
    """
    Proves the signed bytes are genuinely ours — the check a node performs.
    """

    from eth_account import Account as EthAccount

    tx = anchor.build_transaction(
        TEST_ACCOUNT.address, 3, 10**9, 5, CHAIN_HEAD
    )

    raw = anchor.sign_transaction(tx, TEST_ACCOUNT.key)
    recovered = EthAccount.recover_transaction(raw)

    assert recovered == TEST_ACCOUNT.address


def test_signing_handles_both_eth_account_naming_conventions(monkeypatch):
    """
    eth-account renamed rawTransaction -> raw_transaction in 0.13. Guessing
    wrong is a silent AttributeError at the moment the anchor matters.
    """

    class LegacySigned:
        rawTransaction = b"\x01\x02\x03"

    class LegacyAccount:
        @staticmethod
        def sign_transaction(transaction, key):
            return LegacySigned()

    import sys
    import types

    module = types.ModuleType("eth_account")
    module.Account = LegacyAccount
    monkeypatch.setitem(sys.modules, "eth_account", module)

    assert anchor.sign_transaction({}, "0x00") == "0x010203"


def test_signing_reports_an_unknown_eth_account_shape(monkeypatch):
    class Mystery:
        pass

    class MysteryAccount:
        @staticmethod
        def sign_transaction(transaction, key):
            return Mystery()

    import sys
    import types

    module = types.ModuleType("eth_account")
    module.Account = MysteryAccount
    monkeypatch.setitem(sys.modules, "eth_account", module)

    with pytest.raises(RuntimeError, match="unexpected version"):
        anchor.sign_transaction({}, "0x00")


# ============================================================
# THE FULL ANCHOR FLOW
# ============================================================

@pytest.fixture
def anchoring_enabled(monkeypatch):
    monkeypatch.setattr(config, "ANCHORING_ENABLED", True)
    monkeypatch.setattr(config, "CHAIN_PRIVATE_KEY", TEST_ACCOUNT.key.hex())


def test_anchor_head_broadcasts_a_signed_transaction(monkeypatch, anchoring_enabled):
    fake = FakeRpc()
    monkeypatch.setattr(anchor, "rpc", fake)

    record = anchor.anchor_head(10, CHAIN_HEAD)

    assert record is not None
    assert record["blockNumber"] == 10
    assert record["chainHead"] == CHAIN_HEAD
    assert record["txHash"] == "0x" + "ab" * 32
    assert record["from"] == TEST_ACCOUNT.address
    assert record["explorerUrl"].endswith(record["txHash"])

    assert fake.method_names() == [
        "eth_getTransactionCount",
        "eth_gasPrice",
        "eth_sendRawTransaction",
    ]


def test_broadcast_payload_is_valid_and_recoverable(monkeypatch, anchoring_enabled):
    """
    Inspect exactly what would go on-chain.
    """

    from eth_account import Account as EthAccount

    fake = FakeRpc()
    monkeypatch.setattr(anchor, "rpc", fake)

    anchor.anchor_head(77, CHAIN_HEAD)

    sent = fake.calls[-1]
    raw = sent["params"][0]

    assert EthAccount.recover_transaction(raw) == TEST_ACCOUNT.address


def test_anchor_uses_the_nonce_the_chain_reports(monkeypatch, anchoring_enabled):
    fake = FakeRpc(eth_getTransactionCount="0x2a")  # 42
    monkeypatch.setattr(anchor, "rpc", fake)

    anchor.anchor_head(1, CHAIN_HEAD)

    nonce_call = fake.calls[0]
    assert nonce_call["params"] == [TEST_ACCOUNT.address, "pending"]


def test_anchor_is_recorded_and_listable(monkeypatch, anchoring_enabled):
    monkeypatch.setattr(anchor, "rpc", FakeRpc())

    anchor.anchor_head(1, CHAIN_HEAD)
    anchor.anchor_head(2, CHAIN_HEAD)

    assert len(anchor.get_anchors()) == 2
    assert anchor.status()["anchorsWritten"] == 2
    assert anchor.status()["latestAnchor"]["blockNumber"] == 2


# ============================================================
# FAILURE ISOLATION
# ============================================================

def test_rpc_failure_never_raises(monkeypatch, anchoring_enabled):
    """
    A slow or broken testnet must not break a payment decision.
    """

    def exploding(method, params):
        raise RuntimeError("RPC down")

    monkeypatch.setattr(anchor, "rpc", exploding)

    assert anchor.anchor_head(1, CHAIN_HEAD) is None
    assert anchor.get_anchors() == []


def test_rejected_broadcast_never_raises(monkeypatch, anchoring_enabled):
    fake = FakeRpc(eth_sendRawTransaction=RuntimeError("insufficient funds"))
    monkeypatch.setattr(anchor, "rpc", fake)

    assert anchor.anchor_head(1, CHAIN_HEAD) is None


def test_disabled_anchoring_is_a_clean_no_op():
    assert config.ANCHORING_ENABLED is False
    assert anchor.anchor_head(1, CHAIN_HEAD) is None
    assert anchor.status()["enabled"] is False
    assert "disabled" in anchor.status()["note"].lower()


def test_status_never_claims_an_anchor_it_did_not_write():
    status = anchor.status()

    assert status["anchorsWritten"] == 0
    assert status["latestAnchor"] is None


# ============================================================
# PREFLIGHT
# ============================================================

def test_preflight_reports_not_ready_without_a_key():
    result = anchor.preflight()

    assert result["ready"] is False
    assert "AEGIS_CHAIN_PRIVATE_KEY" in result["reason"]


def test_preflight_detects_a_funded_account(monkeypatch, anchoring_enabled):
    monkeypatch.setattr(anchor, "rpc", FakeRpc())

    result = anchor.preflight()

    assert result["ready"] is True
    assert result["address"] == TEST_ACCOUNT.address


def test_preflight_detects_an_unfunded_account(monkeypatch, anchoring_enabled):
    monkeypatch.setattr(anchor, "rpc", FakeRpc(eth_getBalance="0x0"))

    result = anchor.preflight()

    assert result["ready"] is False
    assert "faucet" in result["reason"].lower()


# ============================================================
# INTEGRATION WITH THE LEDGER
# ============================================================

def test_ledger_anchors_on_the_configured_interval(monkeypatch, anchoring_enabled):
    import blockchain

    monkeypatch.setattr(config, "ANCHOR_EVERY", 2)
    monkeypatch.setattr(anchor, "rpc", FakeRpc())

    ledger = config.LEDGER_FILE
    if ledger.exists():
        ledger.unlink()

    for index in range(4):
        blockchain.create_blockchain_record(
            {
                "id": f"req-{index}",
                "task": "t",
                "provider": "OpenWeather",
                "amount": 0,
                "status": "approved",
            }
        )

    # Blocks 2 and 4 anchor; 1 and 3 do not.
    assert [a["blockNumber"] for a in anchor.get_anchors()] == [2, 4]

    if ledger.exists():
        ledger.unlink()
