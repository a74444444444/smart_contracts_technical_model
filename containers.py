from bridge_adapters import BridgeAdapter, BridgeSupport
from datastructures import (ERC20, Address, BridgeInstruction,
                            DepositConfirmation, SwapInstruction,
                            WithdrawalRequest, WithdrawalResponse)
from errors import AuthError
from messaging import Message, Messaging
from swap_router import SwapRouter
from vault import Vault


class Logic:
    def enter(self, tokens: list[ERC20], amounts: list[int]) -> int:
        ...

    def exit(self, liquidity_decrease: int) -> None:
        # liquidity_decrease - amount of liquidity weighted by nav and lp amount and total lp
        ...

    def claim(self) -> None:
        ...

    def emergency_exit(self) -> None:
        ...

    def exit_building_block(self, id_: int) -> None: # ?
        ...

    def nav(self) -> int:
        return 0

    def underlying_liquidity_amount(self) -> int:
        return 0

class ExecutionSupport:
    logics: dict[Logic, bool]

    current_batch_liquidity_growth: int
    current_notion_growth: int

    current_shares_for_withdrawal: int
    current_total_shares: int

    def setLogic(self, logic: Logic, is_whitelisted: bool) -> None:
        self.logics[logic] = is_whitelisted

    def enter_logic(
            self,
            logic: Logic,
            tokens: ERC20,
            amounts: list[int],
            min_liquidity_delta: int,
    ) -> int:
        if not self.logics[logic]:
            raise ValueError("Logic is not whitelisted")
        current_liquidity = logic.underlying_liquidity_amount()
        logic.enter(tokens, amounts)
        liquidity_after = logic.underlying_liquidity_amount()
        delta = liquidity_after - current_liquidity
        self.current_batch_liquidity_growth += delta
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
        logic_nav = logic.underlying_liquidity_amount()
        amount_for_withdraw = logic_nav * self.current_shares_for_withdrawal // self.current_total_shares
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
    vault: Vault
    notion: ERC20
    operator: Address


    def prepare_liquidity(self, swaps: list[SwapInstruction]):
        if "msg.sender" != self.operator:
            raise AuthError("Only operator allowed")
        for swap in swaps:
            self.swap_router.swap(swap)

    def start_withdrawal(self, batch_shares: int, total_shares: int) -> None:
        ...

class PrincipalContainer(Container, Messaging, BridgeSupport):
    whitelisted_bridge_adapter: dict[BridgeAdapter, bool]
    current_batch_liquidity_growth: int
    current_notion_growth: int

    def start_enter(
        self,
        swaps: list[SwapInstruction],
        bridge_adapters: list[BridgeAdapter],
        bridge_instructions: list[BridgeInstruction]
    ) -> None:
        if self.operator != "msg.sender":
            raise ValueError("Only operator allowed")
        if len(bridge_adapters) != len(bridge_instructions):
            raise ValueError("bridge_adapters and bridge_instructions must have same length")

        for swap in swaps:
            self.swap_router.swap(swap)
        for i, instruction in enumerate(bridge_instructions):
            self._validate_bridge_adapter(bridge_adapters[i])
            bridge_adapters[i].bridge(instruction)


    def receive_message(self, message: bytes):
        if type(message) is DepositConfirmation:
            message = DepositConfirmation.from_bytes(message)
            self._claim_deposit_confirmation(message)
        elif type(message) is WithdrawalResponse:
            message = WithdrawalResponse.from_bytes(message)
            self._claim_withdrawal_response(message)

    def claim_bridge(self, bridge_adapter: BridgeAdapter, token: ERC20) -> None:
        self._validate_bridge_adapter(bridge_adapter)
        bridge_adapter.claim(token)

    def _claim_deposit_confirmation(self, message: DepositConfirmation) -> None:
        self.current_batch_liquidity_growth = message.nav_growth
        self.current_notion_growth = message.notion_token_remainder

    def _claim_withdrawal_response(self, message: WithdrawalResponse) -> None:
        ...

    def finalize_enter(
        self,
        bridge_adapters: list[BridgeAdapter],
        swaps: list[SwapInstruction],
        callback: DepositConfirmation
    ) -> None:
        if self.operator != "msg.sender":
            raise ValueError("Only operator allowed")
        for bridge_adapter in bridge_adapters:
            self.claim_bridge(bridge_adapter=bridge_adapter, token=Address(self.notion))
        for swap in swaps:
            self.swap_router.swap(swap)

        # transfer notion if exists?
        self.vault.deposit_container_callback(callback)
        self.current_batch_liquidity_growth = 0
        self.current_notion_growth = 0


    def finalize_exit(self):
        ...

    def start_withdrawal(self, batch_shares: int, total_shares: int) -> None:
        if "msg.sender" != self.vault:
            raise ValueError("Only vault allowed")
        withdrawal_message = WithdrawalRequest(
            shares_for_withdrawal=batch_shares,
            total_shares=total_shares
        )
        self.send_message(withdrawal_message)


class AgentContainer(Container, BridgeSupport, Messaging, ExecutionSupport):
    def claim_bridge(self, bridge_adapter: BridgeAdapter, token: ERC20) -> None:
        """Call n times (n - amount of bridges)"""
        if "msg.sender" != self.operator:
            raise AuthError()
        self._validate_bridge_adapter(bridge_adapter)
        bridge_adapter.claim(token)

    def finalize_remote_enter(
        self,
        bridge_adapters: list[BridgeAdapter],
        bridge_instructions: list[BridgeInstruction]
    ) -> None: # need bridge?
        """
         1. Process bridges in needed (if enters failed)
         2. Send callback with deposit confirmation
         """
        for i, bridge_adapter in enumerate(bridge_adapters):
            bridge_adapter.bridge(bridge_instructions[i])

        callback = DepositConfirmation(
            nav_growth=self.current_batch_liquidity_growth,
            notion_token_remainder=self.current_notion_growth,
        )
        self.current_batch_liquidity_growth = 0
        self.current_notion_growth = 0
        self.send_message(callback)

    def receive_message(self, message: Message) -> None:
        if type(message) is WithdrawalRequest:
            self._claim_withdrawal_request(message)

    def finish_withdrawal_processing(
            self,
            bridge_adapters: list[BridgeAdapter],
            bridges: list[BridgeInstruction],
            swaps: list[SwapInstruction]
    ) -> None:
        self._finish_withdrawal()
        for swap in swaps:
            self.swap_router.swap(swap)
        for i, bridge_adapter in enumerate(bridge_adapters):
            bridge_adapter.bridge(bridges[i])


class LocalContainer(Container, ExecutionSupport):
    ...