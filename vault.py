from containers import Container
from datastructures import (
    ERC20,
    ERC721,
    Address,
    DepositBatch,
    DepositConfirmation,
    PendingDepositBatch,
    PendingWithdrawalBatch,
    Position,
    WithdrawalBatch,
)
from errors import AuthError, NotEnoughShares


class Vault(ERC721):
    # vault configuration
    notion: ERC20
    operator: Address

    # vault state
    total_shares: int = 0
    nav: int = 0


    positions: dict[int, Position] = dict() # position_id -> position data
    positionOwners: dict[int, Address] = dict()
    last_position_index: int = 0


    # Batch states
    deposit_batch: DepositBatch = DepositBatch()
    pending_deposit_batch: PendingDepositBatch = PendingDepositBatch()
    withdrawal_batch: WithdrawalBatch = WithdrawalBatch()
    pending_withdrawal_batch: PendingWithdrawalBatch = PendingWithdrawalBatch()

    current_pending_withdrawal_batch_id: int


    # containers
    containers: list[Container] = []
    weights: dict[Container, int] = dict()
    PRECISION: int = 1000

    # Batch processing
    batchShares: dict[int, int] = dict() # batch_id -> batch shares
    batchNAVs: dict[int, int] = dict()# batch_id -> nav_growth
    batchRemainders: dict[int, int] = dict()# batch_id -> remainder

    withdrawalBatchShares: dict[int, int] = dict()# withdrawal_batch_id -> shares
    claimable: dict[int, int] = dict()# withdrawal batch id -> nav growth

    def __init__(self, notion: ERC20):
        self.notion = notion

    def add_container(self, container: Container, weight: int) -> None:
        self.containers.append(container)
        self.weights[container] = weight

    def create_deposit_request(self, amount: int) -> None:
        """
        User deposits amount of notion token in current batch.

        :param amount: amount of notion token
        :return:
        """
        self.notion.transferFrom("msg.sender", "address(this)", amount)
        self.deposit_batch.buffered_amount += amount
        self.positions[self.last_position_index] = Position(
            notion_amount=amount,
            deposit_batch_id=self.deposit_batch.id_,
        )
        self.positionOwners[self.last_position_index] = "msg.sender"
        self.last_position_index += 1

    def start_current_deposit_batch_processing(self) -> None:
        """
        Distribute current batch between containers
        :return:
        """
        buffered_amount = self.deposit_batch.buffered_amount
        current_deposit_batch_id = self.deposit_batch.id_

        self.deposit_batch.buffered_amount = 0
        self.deposit_batch.id_ += 1
        self.pending_deposit_batch.id = current_deposit_batch_id
        self.pending_deposit_batch.batch_nav = buffered_amount

        for container in self.containers:
            amount = buffered_amount * self.weights[container] // self.PRECISION
            self.notion.transfer(container.address, amount)

    def deposit_container_callback(self, deposit_confirmation: DepositConfirmation) -> None:
        """
        Receive deposit confirmation from container

        :param deposit_confirmation: struct
        :return:
        """
        if deposit_confirmation.notion_token_remainder > 0:
            self.notion.transferFrom("msg.sender", "address(this)", deposit_confirmation.notion_token_remainder)
            self.pending_deposit_batch.notion_token_remainder += deposit_confirmation.notion_token_remainder
        if deposit_confirmation.nav_growth > 0:
            self.pending_deposit_batch.nav_growth += deposit_confirmation.nav_growth
        # todo: think about mark callback from certain container as received

    def reset_pending_deposit_nav_growth(self):
        self.pending_deposit_batch.nav_growth = 0

    def finish_deposit_batch_processing(self) -> None:
        """
        Finish deposit batch processing
        :return:
        """
        batch_notion_remainder = self.pending_deposit_batch.notion_token_remainder
        batch_nav_growth = self.pending_deposit_batch.nav_growth
        if batch_notion_remainder > 0 and batch_nav_growth > 0:
            """Batch can be fully executed or fully reverted"""
            raise Exception("Finalize deposit batch impossible if remainder exists")

        self.pending_deposit_batch.notion_token_remainder = 0
        self.pending_deposit_batch.nav_growth = 0

        if batch_notion_remainder > 0:
            """
            If batch fully reverted: save remainder from all exits for certain batch 
            for allow to users to claim their remainder
            """
            self.batchRemainders[self.pending_deposit_batch.id] = batch_notion_remainder
        if batch_nav_growth > 0:
            """
            If batch fully  executed: mint shares and save batch shares and batch NAV into maps
            for making claim allowed by batch users
            """
            shares = self._issue_shares(batch_nav_growth)
            self.batchShares[self.pending_deposit_batch.id] = shares
            self.batchNAVs[self.pending_deposit_batch.id] = self.pending_deposit_batch.batch_nav


    def claim_remainder_after_deposit(self, position_id: int) -> int:
        """
        Claim tokens from reverted batch
        """
        position = self.positions[position_id]
        positionOwner = self.positionOwners[position_id]

        batch_remainder = self.batchRemainders[position.deposit_batch_id]
        user_amount = position.notion_amount
        batch_amount = self.pending_deposit_batch.batch_nav

        del position
        amount_for_claim = user_amount * batch_remainder // batch_amount
        self.notion.transfer(positionOwner, amount_for_claim)
        return amount_for_claim


    def claim_shares_after_deposit(self, position_id: int) -> None:
        """Claim shares after batch deposit"""
        position = self.positions[position_id]
        batch_total_shares = self.batchShares[position.deposit_batch_id]
        batch_nav = self.batchNAVs[position.deposit_batch_id]
        user_shares = position.notion_amount * batch_total_shares // batch_nav
        position.shares_amount = user_shares
        position.notion_amount = 0


    def create_withdrawal_request(self, position_id: int, shares_amount: int) -> None:
        """
        Create withdrawal request by user from his position for some shares.
        Allowed only for position owner.
        When user creates withdrawal request, amount of shares become
        """
        position = self.positions[position_id]
        owner = self.positionOwners[position_id]
        if "msg.sender" != owner:
            raise AuthError()
        if shares_amount > position.shares_amount:
            raise NotEnoughShares()
        position.shares_amount -= shares_amount
        position.locked_shares_amount += shares_amount
        self.withdrawal_batch.batch_shares_amount += shares_amount

    def start_current_withdrawal_batch_processing(self) -> None:
        """Init withdrawal processing"""
        if "msg.sender" != self.operator:
            raise AuthError()
        batch_shares_amount = self.withdrawal_batch.batch_shares_amount

        self.pending_withdrawal_batch.id_ = self.withdrawal_batch.id_
        self.pending_withdrawal_batch.batch_shares_amount = batch_shares_amount
        self.pending_withdrawal_batch.total_supply_snapshot = self.total_shares

        self.withdrawal_batch.batch_shares_amount = 0
        self.withdrawal_batch.id_ += 1

        for container in self.containers:
            container.start_withdrawal(batch_shares_amount, self.total_shares)

    def withdrawal_container_callback(self, notion_growth: int) -> None:
        """Receive callback from container"""
        if "msg.sender" not in self.containers:
            raise AuthError()
        # notion.transferFrom??
        self.claimable[self.pending_withdrawal_batch.id_] += notion_growth

    def finish_withdrawal_batch_processing(self) -> None:
        """Specify amount of notion tokens for claim by user in batch"""
        if "msg.sender" != self.operator:
            raise AuthError()
        nav_decrease = self.claimable[self.current_pending_withdrawal_batch_id]
        lps = self.pending_withdrawal_batch.batch_shares_amount
        self._burn_shares(nav_decrease, lps)

    def claim_withdrawn_notion_token(self, position_id: int, withdrawal_batch_id: int) -> None:
        position_owner = self.positionOwners[position_id]
        batch_nav = self.batchNAVs[withdrawal_batch_id]
        batch_shares = self.batchShares[withdrawal_batch_id]
        position = self.positions[position_id]
        amount_for_claim = position.locked_shares_amount * batch_nav // batch_shares
        position.locked_shares_amount -= amount_for_claim
        self.notion.transfer(position_owner, amount_for_claim)


    def _issue_shares(self, nav_growth: int) -> int:
        if self.nav == 0:
            shares = nav_growth
        else:
            shares = nav_growth * self.total_shares // self.nav
        self.total_shares += shares
        self.nav += nav_growth
        return shares

    def _burn_shares(self, nav_decrease: int, lp_amount: int) -> None:
        self.total_shares -= lp_amount
        self.nav -= nav_decrease
