from typing import TypeVar


# Messages
class Message:
    def from_bytes(self, raw: bytes) -> "Message":
        raise NotImplementedError()

    def to_bytes(self) -> bytes:
        raise NotImplementedError()

class BridgeMessage(Message):
    container: str

    def from_bytes(self, raw: bytes) -> "BridgeMessage":
        return BridgeMessage(container="")

    def to_bytes(self) -> bytes:
        return b"\x01"

    def __init__(self, container: str):
        self.container = container

class DepositConfirmation(Message):
    nav_growth: int
    notion_token_remainder: int

    def from_bytes(self, raw: bytes) -> "DepositConfirmation":
        return DepositConfirmation(
            nav_growth=0,
            notion_token_remainder=0,
        )

    def to_bytes(self) -> bytes:
        return b"\x02"

    def __init__(self, nav_growth: int, notion_token_remainder: int):
        self.nav_growth = nav_growth
        self.notion_token_remainder = notion_token_remainder


class WithdrawalRequest(Message):
    shares_for_withdrawal: int
    total_shares: int

    def __init__(self, container: str, shares_for_withdrawal: int, total_shares: int):
        self.shares_for_withdrawal = shares_for_withdrawal
        self.total_shares = total_shares

class WithdrawalResponse(Message):
    notion_growth: int


# Position
class Position:
    notion_amount: int
    shares_amount: int
    locked_shares_amount: int
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

class PendingDepositBatch:
    """
    Batch in allocation.
    After allocation started id becomes equal to deposit_batch_id.

    :id: batch id
    :nav_growth: increments after callbacks from container received.
    :notion_token_remainder: amount of notion tokens returned from container if enter failed
    """
    id: int
    nav_growth: int
    notion_token_remainder: int
    batch_nav: int

class WithdrawalBatch:
    """
    Withdrawal batch structure

    :id: withdrawal batch id
    :batch_shares_amount: accumulator for user withdrawals
    """
    id_: int
    batch_shares_amount: int

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

class ERC20(Address):
    address: Address

    def __init__(self, address: Address):
        self.address = address

    def balanceOf(self, owner: Address) -> int:
        return 0

    def totalSupply(self) -> int:
        return 0

    def transfer(self, to: Address, amount: int) -> bool:
        return True

    def transferFrom(self, owner: Address, to: Address, amount: int) -> bool:
        return True


class ERC721(Address):
    address: Address

    def balanceOf(self, owner: Address) -> int:
        return 0

    def transferFrom(self, from_: Address, to: Address, token_id: int) -> bool:
        return True

    def safeTransferFrom(self, owner: Address, to: Address, token_id: int, data: bytes) -> bool:
        return True

