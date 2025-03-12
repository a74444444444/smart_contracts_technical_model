from typing import Dict


class Position:
    id: int
    notion_amount: int
    deposit_batch_id: int # ?
    withdrawal_batch_id: int # ?

    def __init__(self, id_: int, notion_amount: int, deposit_batch_id: int, withdrawal_batch_id: int):
        self.id = id_
        self.notion_amount = notion_amount
        self.deposit_batch_id = deposit_batch_id
        self.withdrawal_batch_id = withdrawal_batch_id

class Swap:
    amount_in: int
    min_amount_out: int
    token_in: int
    token_out: int
    payload: bytes


class Bridge:
    bridge_adapter: str
    token: str
    amount: int
    payload: bytes

class BridgeAdapter:
    claimers: list[str]
    # container => token => balance
    balances: dict[str, dict[str, int]]

    def __init__(self, bridge):
        self.bridge = bridge

    def bridge(self, bridge: Bridge):
        pass

    def claim(self, container: str, token: str):
        # check container
        # transfer amount of tokens to container
        pass


class AcrossBridgeAdapter(BridgeAdapter):
    def handleV3AcrossMessage(self, tokenSent: str, amount: int, relayer: str, message: bytes):
        pass

class SwapRouter:
    def swap(self, swap: Swap) -> None:
        pass

class Message:
    pass

class WithdrawalMessage(Message):
    lp_amount: int
    total_lp: int

    def __init__(self, lp_amount: int, total_lp: int):
        self.lp_amount = lp_amount
        self.total_lp = total_lp


class Container:
    whitelisted_assets: dict[str, bool]
    asset_amount: dict[str, int]
    swap_router: SwapRouter
    vault: str

    def exit(self, lp_amount: int, total_lp: int) -> None:
        ...

    def do_swap(self, swaps: list[Swap]):
        # prepare liquidity
        for s in swaps:
            self.swap_router.swap(s)

    def receive_notion(self, amount: int):
        # notion.safeTransferFrom(vault, address(this), amount)
        pass

    def receive_bridge(self):
        pass

class DepositCallbackMessage(Message):
    total_nav_growth: int
    notion_balance: int

    def __init__(self, nav_growth: int, notion_balance: int):
        self.total_nav_growth = nav_growth
        self.notion_balance = notion_balance


class MessageTransmitter:
    def send_message(self, message: Message):
        # process message sending logic
        pass

class Logic:
    def enter(self, assets: list[str], amounts: list[int]) -> int:
        # enter logic
        pass

    def exit(self, shares: int, total_shares: int) -> None:
        pass

    def nav(self) -> int:
        return 0

class CrossChainContainer(Container, MessageTransmitter):
    operator: str

    current_batch_nav_delta: int
    bridge_adapters: list[BridgeAdapter]
    logics: dict[Logic, bool]

    # withdrawal processing
    shares_for_withdrawal: int
    actual_total_shares: int
    pendingExits: dict[Logic, bool] # use for know which logic already exited

    def do_bridge(self, bridgeInstruction: Bridge) -> None:
        BridgeAdapter(bridgeInstruction.bridge_adapter).bridge(bridgeInstruction)

    def claim_bridge(self, adapter: BridgeAdapter, token: str) -> None:
        if adapter not in self.bridge_adapters:
            raise
        adapter.claim("address(this)", token)

    def remote_enter_logic(self, logic: Logic, assets: list[str], amounts: list[int]) -> None:
        # todo: think about prepare_liquidity

        # delegatecall
        nav_delta = logic.enter(assets, amounts)
        # check delta
        self.current_batch_nav_delta += nav_delta

    def remote_exit_logic(self, logic: Logic):
        if self.pendingExits[logic] == False:
            raise
        logic.exit(self.shares_for_withdrawal, self.current_batch_nav_delta)
        self.pendingExits[logic] = True



    def receive_exit_callback(self, message: WithdrawalMessage):
        self._register_withdrawal_request(
            shares_for_withdrawal=message.lp_amount,
            total_shares=message.total_lp
        )

    def _register_withdrawal_request(self, shares_for_withdrawal: int, total_shares: int) -> None:
        self.shares_for_withdrawal = shares_for_withdrawal
        self.actual_total_shares = total_shares
        for logic in self.logics.keys():
            self.pendingExits[logic] = True

    def send_enter_callback(self, swaps: list[Swap], bridges: list[BridgeAdapter]):
        for s in swaps:
            self.swap_router.swap(s)
        for b in bridges:
            b.bridge(b)

        message = DepositCallbackMessage(
            nav_growth=self.current_batch_nav_delta,
            notion_balance=0 # usdc.balanceOf(address(this))
        )
        self.current_batch_nav_delta = 0
        self.send_message(message)



class Vault:
    # Vault configuration
    notion: str
    containers: list[Container]
    weights: dict[Container, int] # container weights
    precision: int # weights precision
    operator: str # executor

    # Vault state
    nav: int
    total_shares: int
    current_position_index: int

    # Batch state
    current_deposit_batch_id: int
    current_withdrawal_batch_id: int

    buffered_deposit_batch: int  # amount of notion token in current deposit batch
    buffered_withdrawal_batch: int  # amount of LP tokens in current withdrawal batch

    pending_batch_nav_growth: int # nav growth of current pending batch
    pending_batch_usdc_balance: int # usdc balance of current pending batch. If balance > 0, batch cannot be resolved
    pending_batch_lp_growth: int # batch LP growths
    pending_batch_id: int
    enter_callbacks_counter: int # callback for increase LP growth

    positions: Dict[int, Position]
    shares: Dict[int, int] # position id -> shares amount
    batch_shares: Dict[int, int]

    def create_deposit_request(self, amount: int) -> None:
        # Начислить депозит, создать позицию для пользователя (наминтить nft),
        # записать на позицию deposit amount
        # Вопросы:
        # 1. Может ли у пользователя быть больше 1 позиции?
        # 2. Можно ли регулировать текущую позицию (добавлять в нее токены)

        # notion.safeTransferFrom(msg.sender, address(this), amount)
        self.positions[self.current_position_index] = Position(
            id_=self.current_position_index,
            notion_amount=amount,
            deposit_batch_id=self.current_deposit_batch_id,
            withdrawal_batch_id=0
        )
        self.current_position_index += 1
        self.buffered_deposit_batch += amount

    def create_withdrawal_request(self, position_id: int, amount: int) -> None:
        # 1. Сделать лок на LP пользователя
        # 2. Увеличить buffered_withdrawal_batch
        # 3. Задать для позиции withdrawal batch id
        user_shares = self.shares[position_id]
        if user_shares < amount:
            raise
        self.buffered_withdrawal_batch += amount
        self.shares[position_id] -= amount

    def start_deposit_processing(self):
        batch_amount = self.buffered_deposit_batch
        self.buffered_deposit_batch = 0
        self.current_deposit_batch_id += 1
        for container in self.containers:
            # todo: weights
            container_amount = self.weights[container] * batch_amount // self.precision
            container.receive_notion(container_amount)

    def start_withdrawal_processing(self):
        batch_amount = self.buffered_withdrawal_batch
        self.buffered_withdrawal_batch = 0
        self.current_withdrawal_batch_id += 1
        for container in self.containers:
            container.exit(batch_amount, self.total_shares)


    def start_withdrawal_processing(self, withdrawal_batch_id: int):
        # like in withdrawal processing
        for c in self.containers:
            self.send_withdrawal_request(c, withdrawal_batch_id)

    def send_withdrawal_request(self, container: Container, withdrawal_batch_id: int):
        # TODO: send callback
        pass

    def container_enter_callback(self, batch_id: int, nav_growth: int, usdc_balance: int):
        self.pending_batch_nav_growth += nav_growth
        self.pending_batch_usdc_balance += usdc_balance
        self.pending_batch_id = batch_id
        self.enter_callbacks_counter += 1

    def finalize_batch(self):
        if self.enter_callbacks_counter != len(self.containers):
            raise
        if self.pending_batch_usdc_balance > 0:
            raise
        batch_shares = self.pending_batch_nav_growth *  self.total_shares // self.nav
        self.batch_shares[self.pending_batch_id] = batch_shares
        self.pending_batch_lp_growth = batch_shares
        self.nav += self.pending_batch_nav_growth
        self.total_shares += batch_shares

    def claim_shares(self, position_id: int):
        position = self.positions[position_id]
        user_deposit = position.notion_amount
        shares_amount = user_deposit * self.pending_batch_lp_growth // self.pending_batch_nav_growth
        self.shares[position_id] += shares_amount
        self.positions[position_id].notion_amount = 0
        self.batch_shares[position.deposit_batch_id] -= shares_amount

class LocalContainer(Container, MessageTransmitter):
    operator: str
    pending_batch_id: int
    vault: Vault

    def claim_bridge(self, adapter: BridgeAdapter, token: str) -> None:
        adapter.claim("address(this)", token)

    def enter(self, batch_id: int, swaps: list[Swap], bridges: list[Bridge]):
        # todo: check route for swap + bridge, check operator
        for s in swaps:
            self.swap_router.swap(s)
        for b in bridges:
            BridgeAdapter(b.bridge_adapter).bridge(b)
        self.pending_batch_id = batch_id

    def exit(self, lp_amount: int, total_lp: int) -> None:
        message = WithdrawalMessage(
            lp_amount=lp_amount,
            total_lp=total_lp
        )
        self.send_message(message)


    def finalize_exit_batch(self, ):

    def finalize_enter_batch(self, message: DepositCallbackMessage):
        self.vault.container_enter_callback(
            batch_id=self.pending_batch_id,
            nav_growth=message.total_nav_growth,
            usdc_balance=message.usdc_balance
        )





