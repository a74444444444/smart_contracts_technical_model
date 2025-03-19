from bridge_adapters import BridgeAdapter, BridgeSupport
from datastructures import (
    ERC20,
    Address,
    BridgeInstruction,
    SwapInstruction,
    WithdrawalRequest,
    WithdrawalResponse,
    SuccessDepositConfirmation,
    ContainerMessage
)
from messaging import Message, Messaging
from swap_router import SwapRouter
from typing import Generic, TypeVar

T = TypeVar('T')

class Vault(Generic[T]):
    ...

class Logic:
    logic_nav: int = 48 # technical value

    def enter(self, tokens: list[ERC20], amounts: list[int]) -> int:
        ...

    def exit(self, liquidity_decrease: int) -> None:
        # liquidity_decrease - amount of liquidity weighted by nav and lp amount and total lp
        ...

    def harvest(self) -> None:
        ...

    def emergency_exit(self) -> None:
        ...

    def exit_building_block(self, id_: int) -> None: # ?
        ...

    def nav(self) -> int:
        current_nav = self.logic_nav
        self.logic_nav += 48
        return current_nav

    def underlying_liquidity_amount(self) -> int:
        return 0

class ExecutionSupport:
    logics: dict[Logic, bool] = dict()

    nav_after_harvest: int = 0
    nav_after_harvest_and_enter: int = 0

    shares_for_withdraw: int = 0
    total_shares: int = 0

    def setLogic(self, logic: Logic, is_whitelisted: bool) -> None:
        self.logics[logic] = is_whitelisted

    def enter_logic(
            self,
            logic: Logic,
            tokens: list[ERC20],
            amounts: list[int],
            min_liquidity_delta: int,
    ) -> int:
        if not self.logics[logic]:
            raise ValueError("Logic is not whitelisted")
        logic.harvest()
        self.nav_after_harvest += logic.nav()
        logic.enter(tokens, amounts)
        self.nav_after_harvest_and_enter += logic.nav()
        delta = self.nav_after_harvest_and_enter - self.nav_after_harvest
        if delta < min_liquidity_delta:
            raise ValueError("Slippage failed")
        return delta

    def exit_logic(
        self,
        logic: Logic,
        expected_tokens: list[ERC20],
        min_tokens_deltas: list[int]
    ) -> None:
        if not self.logics[logic]:
            raise ValueError("Logic is not whitelisted")
        deltas = []
        for token in expected_tokens:
            deltas.append(
                token.balanceOf("address(this)")
            )
        logic_lps = logic.underlying_liquidity_amount()
        amount_for_withdraw = (logic_lps * self.current_shares_for_withdrawal) // self.current_total_shares
        logic.exit(liquidity_decrease=amount_for_withdraw)
        for i, token in enumerate(expected_tokens):
            token_delta = token.balanceOf("address(this)") - deltas[i]
            if token_delta < min_tokens_deltas[i]:
                raise ValueError("Slippage failed")

    def _claim_withdrawal_request(self, message: WithdrawalRequest) -> None:
        self.current_shares_for_withdrawal = message.shares_for_withdrawal
        self.current_total_shares = message.total_shares

    def _finish_withdrawal(self):
        self.current_shares_for_withdrawal = 0
        self.current_total_shares = 0



class Container:
    swap_router: SwapRouter
    vault: Address
    notion: ERC20
    operator: Address
    address: str = "0x0000000000000000000000000000000000000002"

    def __init__(self, swap_router: SwapRouter, notion: ERC20) -> None:
        self.swap_router = swap_router
        self.notion = notion

    def prepare_liquidity(self, swaps: list[SwapInstruction]):
        """
        Do some swaps before some actions.
        """
        for swap in swaps:
            self.swap_router.swap(swap)

    def start_withdrawal(self, batch_shares: int, total_shares: int) -> None:
        ...

class PrincipalContainer(Container, Messaging, BridgeSupport):
    container_nav_after_harvest: int = 0
    container_nav_after_enter: int = 0
    vault: "Vault"

    def __init__(self, vault: "Vault", swap_router: SwapRouter, notion: ERC20) -> None:
        Container.__init__(self, swap_router, notion)
        self.vault = vault

    # Enter processing
    def start_enter(
        self,
        swaps: list[SwapInstruction],
        bridge_adapters: list[BridgeAdapter],
        bridge_instructions: list[BridgeInstruction]
    ) -> None:
        """
        Start enter processing on principal side.
        Awaits amount of notion tokens on Principal contract
        Can process optional swaps and bridges for sending funds to remote container's Agent
        """
        if len(bridge_adapters) != len(bridge_instructions):
            raise ValueError("bridge_adapters and bridge_instructions must have same length")

        self.prepare_liquidity(swaps)
        for i, instruction in enumerate(bridge_instructions):
            bridge_adapters[i].bridge(instruction)

    def _claim_deposit_confirmation(self, message: SuccessDepositConfirmation) -> None:
        """
        After success enters into logics on remote chain happens, Agent sends to Principal
        deposit confirmation.
        Fields:
        * container_nav_after_harvest
        * container_nav_after_enter
        """
        self.container_nav_after_harvest = message.nav_after_harvest
        self.container_nav_after_enter = message.nav_after_harvest_and_enter

    def finalize_enter(
        self,
        bridge_adapters: list[BridgeAdapter],
        swaps: list[SwapInstruction],
    ) -> None:
        """
        After receiving deposit confirmation (cross-chain message) and bridge receiving bridge adapters,
        possible to claim tokens, swap it (if necessary) into notion token and execute callback on vault
        for unlock batch actions for users (user actions - claim shares or notion tokens from failed batch)
        As a result - we should have nav growth and notion token remainder
        """
        for bridge_adapter in bridge_adapters:
            self.claim_bridge(bridge_adapter=bridge_adapter, token=Address(self.notion))
        notion_before = self.notion.balanceOf("address(this)")
        self.prepare_liquidity(swaps) # swap to notion
        notion_after = self.notion.balanceOf("address(this)")

        # transfer notion if exists?
        self.vault.deposit_container_callback(
            nav_after_harvest=self.container_nav_after_harvest,
            nav_after_harvest_and_enter=self.container_nav_after_enter,
            notion_token_remainder=notion_after - notion_before,
        )
        if notion_after - notion_before > 0:
            self.notion.transfer(self.vault, notion_after - notion_before)


    def start_withdrawal(self, batch_shares: int, total_shares: int) -> None:
        """
        Send message to remote chain for process withdrawal.
        WithdrawalRequest consists of:
        1) amount of shares (how many shares need to redeem);
        2) total shares amount on withdrawal request moment
        """
        if "msg.sender" != self.vault:
            raise ValueError("Only vault allowed")
        withdrawal_message = WithdrawalRequest(
            shares_for_withdrawal=batch_shares,
            total_shares=total_shares
        )
        self.send_message(withdrawal_message)

    def _claim_withdrawal_response(self) -> None:
        ...


    def finalize_exit(
            self,
            bridge_adapters: list[BridgeAdapter],
            tokens: list[ERC20],
            swaps: list[SwapInstruction]
    ) -> None:
        notion_token_before = self.notion.balanceOf("address(this)")
        for i, bridge_adapter in enumerate(bridge_adapters):
            bridge_adapter.claim(token=tokens[i])
        self.prepare_liquidity(swaps)
        notion_token_after = self.notion.balanceOf("address(this)")
        self.vault.withdrawal_container_callback(
            notion_growth=notion_token_after - notion_token_before
        )


    def receive_message(self, message: bytes):
        if type(message) is SuccessDepositConfirmation:
            message = SuccessDepositConfirmation.from_bytes(message)
            self._claim_deposit_confirmation(message)
        elif type(message) is WithdrawalResponse:
            message = WithdrawalResponse.from_bytes(message)
            self._claim_withdrawal_response(message)

    def claim_bridge(self, bridge_adapter: BridgeAdapter, token: ERC20) -> None:
        self._validate_bridge_adapter(bridge_adapter)
        bridge_adapter.claim(token)

class AgentContainer(Container, BridgeSupport, Messaging, ExecutionSupport):
    def finalize_success_enters(self) -> None: # need bridge?
        """
        Send callback about success enters
        Sent parameters:
        * nav_after_harvest - nav after harvest in all logics
        * nav after enter - nav after harvest in all logics and enters
        """
        callback = SuccessDepositConfirmation(
            nav_after_harvest=self.nav_after_harvest,
            nav_after_harvest_and_enter=self.nav_after_harvest_and_enter,
        )
        self.nav_after_harvest = 0
        self.nav_after_harvest_and_enter = 0
        self.send_message(callback)

    def return_funds(
        self,
        bridge_adapters: list[BridgeAdapter],
        bridge_instructions: list[BridgeInstruction]
    ) -> None:
        """
        Return receipts after failed enters
        """
        # TODO: token whitelisting, may be batch accounting for prevent some bad spending
        # TODO: think about some verifications (message with amounts or something like this)

        for i, bridge_adapter in enumerate(bridge_adapters):
            bridge_adapter.bridge(bridge_instructions[i])

    def finish_withdrawal_processing(
        self,
        bridge_adapters: list[BridgeAdapter],
        bridges: list[BridgeInstruction],
        swaps: list[SwapInstruction]
    ) -> None:
        self._finish_withdrawal()
        self.prepare_liquidity(swaps)
        for i, bridge_adapter in enumerate(bridge_adapters):
            bridge_adapter.bridge(bridges[i])

    def receive_message(self, message: Message) -> None:
        if type(message) is WithdrawalRequest:
            self._claim_withdrawal_request(message)


class LocalContainer(Container, ExecutionSupport):
    ...