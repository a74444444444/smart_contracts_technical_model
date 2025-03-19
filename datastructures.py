from enum import Enum
from typing import TypeVar, Generic
from eth_abi import encode, decode

class MessageType(Enum):
    DEPOSIT_CONFIRMATION = 0
    WITHDRAWAL_REQUEST = 1
    WITHDRAWAL_RESPONSE = 2

# Messages
class Message:
    def from_bytes(self, raw: bytes) -> "Message":
        raise NotImplementedError()

    def to_bytes(self) -> bytes:
        raise NotImplementedError()

class ContainerMessage(Message):
    type: MessageType
    payload: bytes

    def to_bytes(self) -> bytes:
        return encode(["uint8", "bytes"], [self.type.value, self.payload])

    def __init__(self, type: MessageType, data: bytes):
        self.type = type
        self.payload = data

class BridgeMessage(Message):
    container: str

    def from_bytes(self, raw: bytes) -> "BridgeMessage":
        decoded = decode(["address"], raw)[0]
        return BridgeMessage(container=decoded)

    def to_bytes(self) -> bytes:
        return encode(["address"], [self.container])

    def __init__(self, container: str):
        self.container = container

class SuccessDepositConfirmation(Message):
    nav_after_harvest: int = 0
    nav_after_harvest_and_enter: int = 0

    def to_bytes(self) -> bytes:
        return encode(["uint256", "uint256"], [self.nav_after_harvest, self.nav_after_harvest_and_enter])

    def from_bytes(self, raw: bytes) -> "SuccessDepositConfirmation":
        nav_after_harvest, nav_after_harvest_and_enter = decode(["uint256", "uint256"], raw)
        return SuccessDepositConfirmation(
            nav_after_harvest=nav_after_harvest,
            nav_after_harvest_and_enter=nav_after_harvest_and_enter,
        )

    def __init__(self, nav_after_harvest: int, nav_after_harvest_and_enter: int):
        self.nav_after_harvest = nav_after_harvest
        self.nav_after_harvest_and_enter = nav_after_harvest_and_enter

class WithdrawalRequest(Message):
    shares_for_withdrawal: int
    total_shares: int

    def __init__(self, container: str, shares_for_withdrawal: int, total_shares: int):
        self.shares_for_withdrawal = shares_for_withdrawal
        self.total_shares = total_shares

class WithdrawalResponse:
    nav_after_harvest: int
    nav_after_harvest_and_enter: int

    def __init__(self, nav_after_harvest: int, nav_after_harvest_and_enter: int):
        self.nav_after_harvest = nav_after_harvest
        self.nav_after_harvest_and_enter = nav_after_harvest_and_enter


# Position
class Position:
    notion_amount: int
    shares_amount: int
    locked_shares_amount: int = 0
    deposit_batch_id: int
    withdrawal_batch_id: int

    def __init__(self, notion_amount: int, deposit_batch_id: int):
        self.notion_amount = notion_amount
        self.shares_amount = 0
        self.deposit_batch_id = deposit_batch_id
        self.withdrawal_batch_id = 0


class Instruction:
    ...

class BridgeInstruction(Instruction):
    token: str
    amount: int
    message: Message
    payload: bytes

    def __init__(self, token: str, amount: int, payload: bytes):
        self.token = token
        self.amount = amount
        self.payload = payload

class SwapInstruction(Instruction):
    amount_in: int
    min_amount_out: int
    token_in: str
    token_out: str
    payload: bytes

    def __init__(self, amount_in: int, min_amount_out: int, token_in: str, token_out: str, payload: bytes):
        self.amount_in = amount_in
        self.min_amount_out = min_amount_out
        self.token_in = token_in
        self.token_out = token_out
        self.payload = payload

# Batches
class DepositBatch:
    """
    Batch before allocation.
    Used for filling current batch.

    :id: current batch id, increments after allocation.
    :buffered_amount: - how many notion tokens users brought in current batch. Sets to zero after allocation.
    """
    id_: int
    buffered_amount: int

    def __init__(self):
        self.id_ = 0
        self.buffered_amount = 0

class PendingDepositBatch:
    """
    Batch in allocation.
    After allocation started id becomes equal to deposit_batch_id.

    :id: batch id
    :nav_growth: increments after callbacks from container received.
    :notion_token_remainder: amount of notion tokens returned from container if enter failed
    """
    id: int = 0
    notion_token_remainder: int = 0
    batch_nav: int = 0
    nav_after_harvest: int = 0
    nav_after_harvest_and_enter: int = 0
    processed_containers: list = []

class WithdrawalBatch:
    """
    Withdrawal batch structure

    :id: withdrawal batch id
    :batch_shares_amount: accumulator for user withdrawals
    """
    id_: int = 0
    batch_shares_amount: int = 0

class PendingWithdrawalBatch:
    """
    Processing withdraw batch structure

    :id: withdrawal batch id
    :batch_shares_amount: batch shares amount
    :total_supply_snapshot: total supply at the moment of withdrawal processing
    :notion_token_remainder: amount of notion tokens received from containers after withdrawals
    """
    id_: int
    batch_shares_amount: int
    total_supply_snapshot: int
    notion_token_remainder: int


# Technical
Address = TypeVar('Address')

class ERC20(Generic[Address]):
    address: Address
    name: str

    def __init__(self, address: Address, name: str = ""):
        self.address = address
        self.name = name

    def balanceOf(self, owner: Address) -> int:
        return 0

    def totalSupply(self) -> int:
        return 0

    def transfer(self, to: Address, amount: int) -> bool:
        return True

    def transferFrom(self, owner: Address, to: Address, amount: int) -> bool:
        return True


class ERC721(Generic[Address]):
    address: Address

    def balanceOf(self, owner: Address) -> int:
        return 0

    def transferFrom(self, from_: Address, to: Address, token_id: int) -> bool:
        return True

    def safeTransferFrom(self, owner: Address, to: Address, token_id: int, data: bytes) -> bool:
        return True

