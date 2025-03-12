from datastructures import Position, Address, ERC20, DepositConfirmation, WithdrawalResponse
from containers import Container
from errors import AuthError, FinalizeDepositBatchImpossible, NotEnoughShares

class Vault:
    # vault configuration
    notion: ERC20
    operator: Address

    # vault state
    total_shares: int
    nav: int


    positions: dict[int, Position] # position_id -> position data
    positionOwners: dict[int, Address]
    last_position_index: int = 0

    # Batch processing
    # Deposit batch init params
    current_deposit_batch_buffered_amount: int
    current_deposit_batch_id: int
    current_pending_deposit_batch_id: int
    current_deposit_nav_growth: int
    # current_deposit_usdc_balance: int ?
    current_deposit_callbacks_received: int

    current_withdrawal_batch_buffered_amount: int
    current_withdrawal_batch_id: int
    current_withdrawal_nav_growth: int
    current_withdrawal_callbacks_received: int
    current_pending_withdrawal_batch_id: int


    # containers
    containers: list[Container]
    weights: dict[Container, int]
    PRECISION: int

    # Batch processing
    batchShares: dict[int, int] # batch_id -> batch shares
    batchNAVs: dict[int, int] # batch_id -> nav_growth

    withdrawalBatchShares: dict[int, int] # withdrawal_batch_id -> shares
    claimable: dict[int, int] # withdrawal batch id -> nav growth


    def create_deposit_request(self, amount: int) -> None:
        self.notion.transferFrom("msg.sender", "address(this)", amount)
        self.current_deposit_batch_buffered_amount += amount
        self.positions[self.last_position_index] = Position(
            notion_amount=amount,
            deposit_batch_id=self.current_deposit_batch_id,
        )
        self.positionOwners[self.last_position_index] = Address("msg.sender")
        self.last_position_index += 1

    def start_current_deposit_batch_processing(self) -> None:
        if self.operator != "msg.sender":
            raise AuthError()
        buffered_amount = self.current_deposit_batch_buffered_amount
        self.current_deposit_batch_buffered_amount = 0
        self.current_pending_deposit_batch_id = self.current_deposit_batch_id
        self.current_deposit_batch_id += 1
        for container in self.containers:
            amount = buffered_amount * self.weights[container] // self.PRECISION
            self.notion.transfer(Address(container), amount)

    def deposit_container_callback(self, deposit_confirmation: DepositConfirmation) -> None:
        if "msg.sender" not in self.containers:
            raise AuthError()
        self.current_deposit_nav_growth += deposit_confirmation.nav_growth
        self.current_deposit_callbacks_received += 1

    def finish_deposit_batch_processing(self) -> None:
        if "msg.sender" != self.operator:
            raise AuthError()
        if self.current_deposit_callbacks_received != len(self.containers):
            raise FinalizeDepositBatchImpossible()
        batch_nav_growth = self.current_deposit_nav_growth
        self.current_deposit_nav_growth = 0
        self.current_deposit_callbacks_received = 0
        shares = self._issue_shares(batch_nav_growth)
        self.batchShares[self.current_pending_deposit_batch_id] = shares
        self.batchNAVs[self.current_pending_deposit_batch_id] = batch_nav_growth


    def claim_shares_after_deposit(self, position_id: int) -> None:
        position = self.positions[position_id]
        batch_total_shares = self.batchShares[position.deposit_batch_id]
        batch_nav = self.batchNAVs[position.deposit_batch_id]
        user_shares = position.notion_amount * batch_total_shares // batch_nav
        position.shares_amount = user_shares
        position.notion_amount = 0


    def create_withdrawal_request(self, position_id: int, shares_amount: int) -> None:
        position = self.positions[position_id]
        owner = self.positionOwners[position_id]
        if "msg.sender" != owner:
            raise AuthError()
        if shares_amount > position.shares_amount:
            raise NotEnoughShares()
        position.shares_amount -= shares_amount
        position.locked_shares_amount += shares_amount
        self.current_withdrawal_batch_buffered_amount += shares_amount

    def start_current_withdrawal_batch_processing(self) -> None:
        batch_shares_amount = self.current_withdrawal_batch_buffered_amount
        self.withdrawalBatchShares[self.current_withdrawal_batch_id] = batch_shares_amount
        self.current_pending_withdrawal_batch_id = self.current_withdrawal_batch_id
        self.current_withdrawal_batch_buffered_amount = 0
        self.current_withdrawal_batch_id += 1
        for container in self.containers:
            container.start_withdrawal(batch_shares_amount, self.total_shares)

    def withdrawal_container_callback(self, withdrawal_callback: WithdrawalResponse) -> None:
        self.claimable[self.current_pending_withdrawal_batch_id] += withdrawal_callback.notion_growth
        self.current_withdrawal_callbacks_received += 1

    def finish_withdrawal_batch_processing(self) -> None:
        if self.current_withdrawal_callbacks_received != len(self.containers):
            raise
        self.current_withdrawal_callbacks_received = 0
        nav_decrease = self.claimable[self.current_pending_withdrawal_batch_id]
        lps = self.withdrawalBatchShares[self.current_pending_withdrawal_batch_id]
        self._burn_shares(nav_decrease, lps)


    def claim_withdrawn_notion_token(self, position_id: int, withdrawal_batch_id: int) -> None:
        batch_nav = self.batchNAVs[withdrawal_batch_id]
        batch_shares = self.batchShares[withdrawal_batch_id]
        position = self.positions[position_id]
        amount_for_claim = position.locked_shares_amount * batch_nav // batch_shares
        position.locked_shares_amount -= amount_for_claim
        self.notion.transfer(Address("msg.sender"), amount_for_claim)


    def _issue_shares(self, nav_growth: int) -> int:
        shares = nav_growth * self.total_shares // self.nav
        self.total_shares += shares
        self.nav += nav_growth
        return shares

    def _burn_shares(self, nav_decrease: int, lp_amount: int) -> None:
        self.total_shares -= lp_amount
        self.nav -= nav_decrease
