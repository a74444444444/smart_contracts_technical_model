from typing import TypeVar

# Messages
class Message:
    ...

class BridgeMessage(Message):
    container: str

    @classmethod
    def decode(cls, message: bytes) -> "BridgeMessage":
        return BridgeMessage(container="from bytes")

    def __init__(self, container: str):
        self.container = container

class DepositConfirmation(Message):
    container: str
    nav_growth: int
    notion_token_remainder: int

    def __init__(self, nav_growth: int, notion_token_remainder: int, container: str):
        self.container = container
        self.nav_growth = nav_growth
        self.notion_token_remainder = notion_token_remainder


class WithdrawalRequest(Message):
    container: str
    shares_for_withdrawal: int
    total_shares: int

    def __init__(self, container: str, shares_for_withdrawal: int, total_shares: int):
        self.container = container
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

