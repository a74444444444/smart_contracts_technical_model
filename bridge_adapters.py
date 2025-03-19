from collections import defaultdict

from datastructures import ERC20, BridgeInstruction, BridgeMessage
from eth_abi import decode


class BridgeAdapter:
    # holder => token => amount
    claimable: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def bridge(self, bridgeInstruction: BridgeInstruction):
        ...

    def _receiveBridge(self, for_: str, token: str, amount: int):
        self.claimable[for_][token] += amount

    def claim(self, token: str):
        available = self.claimable["msg.sender"][token]
        ERC20(token).transfer("msg.sender", available)

class AcrossBridgeAdapter(BridgeAdapter):
    # Certain bridge
    def handleV3AcrossMessage(self, token: str, amount: int, recipient: str, data: bytes):
        bridgeMessage = BridgeMessage(
            container=decode(["address"], data)[0]
        )
        self._receiveBridge(bridgeMessage.container, token, amount)

class CCTPBridgeAdapter(BridgeAdapter):
    def cctpReceiveMessage(self, token: str, amount: int, recipient: str, data: bytes):
        bridgeMessage = BridgeMessage(
            container=decode(["address"], data)[0]
        )
        self._receiveBridge(bridgeMessage.container, token, amount)

class BridgeSupport:
    whitelistedBridgeAdapters: dict[BridgeAdapter, bool]

    def set(self, bridgeAdapter: BridgeAdapter, is_whitelisted: bool):
        self.whitelistedBridgeAdapters[bridgeAdapter] = is_whitelisted

    def claim_bridge(self, bridge_adapter: BridgeAdapter, token: str):
        bridge_adapter.claim(token)

    def _validate_bridge_adapter(self, bridge_adapter: BridgeAdapter):
        if bridge_adapter not in self.whitelistedBridgeAdapters:
            raise ValueError("Bridge adapter is not whitelisted")
