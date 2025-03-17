from collections import defaultdict

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
    operator: Address = "0x0"

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

    # containers
    containers: list[Container] = []
    weights: dict[Container, int] = dict()
    PRECISION: int = 1000

    # Batch processing
    depositBatchNotionSent: dict[int, int] = dict()
    depositBatchShares: dict[int, int] = dict() # batch_id -> batch shares
    depositBatchRemainders: dict[int, int] = dict() # batch_id -> remainder

    withdrawalBatchShares: dict[int, int] = defaultdict(int) # withdrawal_batch_id -> shares
    withdrawalBatchNAVs: dict[int, int] = defaultdict(int)

    def __init__(self, notion: ERC20):
        self.notion = notion

    def add_container(self, container: Container, weight: int) -> None:
        self.containers.append(container)
        self.weights[container] = weight

    def create_deposit_request(self, amount: int) -> None:
        """
        User deposits amount of notion token in current batch.
        User deposit represents as position. Each user deposit = new position

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
        As a result, during deposit callback receiving process
        of notion_token_remainder > 0 or nav_growth > 0, not together
        :param deposit_confirmation: struct
        :return:
        """
        container_remainder = deposit_confirmation.notion_token_remainder
        container_nav_growth = deposit_confirmation.nav_growth

        if container_remainder > 0 and container_nav_growth > 0:
            raise Exception("Container enter fully processed or fully canceled")

        batch_total_remainder = self.pending_deposit_batch.notion_token_remainder
        if batch_total_remainder > 0 and container_nav_growth > 0:
            raise Exception("If some enter failed in batch, need to cancel enters in other containers")

        if batch_total_remainder == 0 and container_remainder > 0:
            self._reset_pending_deposit_nav_growth()

        if container_remainder > 0:
            """Claim notion token remainder from container"""
            self.notion.transferFrom("msg.sender", "address(this)", deposit_confirmation.notion_token_remainder)
            self.pending_deposit_batch.notion_token_remainder += deposit_confirmation.notion_token_remainder
            self.pending_deposit_batch.processed_containers.append("msg.sender")
        elif container_nav_growth > 0:
            self.pending_deposit_batch.nav_growth += deposit_confirmation.nav_growth
            self.pending_deposit_batch.processed_containers.append("msg.sender")

    def _reset_pending_deposit_nav_growth(self):
        # todo: think about better solution
        # need to reset nav growth in case where enter in some container
        # failed during the batch deposit processing happen
        self.pending_deposit_batch.nav_growth = 0
        self.pending_deposit_batch.processed_containers = [] # mark that need to process all containers again (for withdraw funds)

    def finish_deposit_batch_processing(self) -> None:
        """
        Finish deposit batch processing
        :return:
        """
        batch_notion_remainder = self.pending_deposit_batch.notion_token_remainder
        batch_nav_growth = self.pending_deposit_batch.nav_growth
        if batch_notion_remainder > 0 and batch_nav_growth > 0:
            """Batch can be fully executed or fully reverted"""
            raise Exception("Batch fully executed or fully reverted")
        if len(self.pending_deposit_batch.processed_containers) != len(self.containers):
            raise Exception("Container has not been processed")

        self.pending_deposit_batch.notion_token_remainder = 0
        self.pending_deposit_batch.nav_growth = 0
        self.pending_deposit_batch.processed_containers = []
        self.depositBatchNotionSent[self.pending_deposit_batch.id] = self.pending_deposit_batch.batch_nav

        if batch_notion_remainder > 0:
            """
            If batch fully reverted: save remainder from all exits for certain batch 
            for allow to users to claim their remainder
            """
            self.depositBatchRemainders[self.pending_deposit_batch.id] = batch_notion_remainder
        if batch_nav_growth > 0:
            """
            If batch fully  executed: mint shares and save batch shares and batch NAV into maps
            for making claim allowed by batch users
            """
            shares = self._issue_shares(batch_nav_growth) # todo: think about mint ordering: in moment of batch processing or claim by user
            self.depositBatchShares[self.pending_deposit_batch.id] = shares


    def claim_remainder_after_deposit(self, position_id: int) -> int:
        """
        Claim tokens from reverted batch
        """
        position = self.positions[position_id]
        positionOwner = self.positionOwners[position_id]

        batch_remainder = self.depositBatchRemainders[position.deposit_batch_id]
        if batch_remainder == 0:
            raise Exception("Batch has not been processed")

        user_amount = position.notion_amount
        if user_amount == 0:
            raise Exception("User has not been deposited")
        batch_amount = self.depositBatchNotionSent[position.deposit_batch_id]

        amount_for_claim = user_amount * batch_remainder // batch_amount
        self.notion.transfer(positionOwner, amount_for_claim)
        del position # Remove position because it actually does not exists if deposit failed
        return amount_for_claim


    def claim_shares_after_deposit(self, position_id: int) -> None:
        """Claim shares after batch deposit"""
        position = self.positions[position_id]
        batch_total_shares = self.depositBatchShares[position.deposit_batch_id]
        if batch_total_shares == 0:
            raise Exception("Batch has not been processed")
        batch_nav = self.depositBatchNotionSent[position.deposit_batch_id]
        user_shares = (position.notion_amount * batch_total_shares) // batch_nav
        position.shares_amount = user_shares
        position.notion_amount = 0


    def create_withdrawal_request(self, position_id: int, shares_amount: int) -> None:
        """
        Create withdrawal request by user from his position for some shares.
        Allowed only for position owner.
        When user creates withdrawal request, amount of shares become
        """
        position = self.positions[position_id] # todo: check if position exists
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
        batch_shares_amount = self.withdrawal_batch.batch_shares_amount

        self.pending_withdrawal_batch.id_ = self.withdrawal_batch.id_
        self.pending_withdrawal_batch.batch_shares_amount = batch_shares_amount
        self.pending_withdrawal_batch.total_supply_snapshot = self.total_shares

        self.withdrawal_batch.batch_shares_amount = 0
        self.withdrawal_batch.id_ += 1

        for container in self.containers:
            container.start_withdrawal(batch_shares_amount, self.pending_withdrawal_batch.total_supply_snapshot)

    def withdrawal_container_callback(self, notion_growth: int) -> None:
        """
        Receive callback from container
        Withdraw result - only received notion token. All swaps should happens in container
        """
        self.notion.transferFrom("msg.sender", "address(this)", notion_growth)
        self.withdrawalBatchNAVs[self.pending_withdrawal_batch.id_] += notion_growth

    def finish_withdrawal_batch_processing(self) -> None:
        """Specify amount of notion tokens for claim by user in batch"""
        nav_decrease = self.withdrawalBatchNAVs[self.pending_withdrawal_batch.id_]
        lps = self.pending_withdrawal_batch.batch_shares_amount
        self.withdrawalBatchShares[self.pending_withdrawal_batch.id_] = lps
        self._burn_shares(nav_decrease, lps)

    def claim_withdrawn_notion_token(self, position_id: int, withdrawal_batch_id: int) -> int:
        position_owner = self.positionOwners[position_id]
        batch_nav = self.withdrawalBatchNAVs[withdrawal_batch_id]
        batch_shares = self.withdrawalBatchShares[withdrawal_batch_id]
        if batch_shares == 0:
            raise Exception("Batch has not been processed")
        position = self.positions[position_id]
        amount_for_claim = (position.locked_shares_amount * batch_nav) // batch_shares
        position.locked_shares_amount -= amount_for_claim
        self.notion.transfer(position_owner, amount_for_claim)
        return amount_for_claim


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
