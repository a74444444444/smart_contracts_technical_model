from datastructures import BridgeInstruction, BridgeMessage, ERC20

class BridgeAdapter:
    # holder => token => amount
    claimable: dict[str, dict[str, int]]

    def bridge(self, bridgeInstruction: BridgeInstruction):
        ...

    def _receiveBridge(self, for_: str, token: str, amount: int):
        self.claimable[for_][ERC20(token)] += amount

    def claim(self, token: ERC20):
        available = self.claimable["msg.sender"][token]
        token.transfer("msg.sender", available)

class AcrossBridgeAdapter(BridgeAdapter):
    # Certain bridge
    def handleV3AcrossMessage(self, token: str, amount: int, recipient: str, data: bytes):
        bridgeMessage = BridgeMessage.decode(data)
        self._receiveBridge(bridgeMessage.container, token, amount)

class CCTPBridgeAdapter(BridgeAdapter):
    def cctpReceiveMessage(self, token: str, amount: int, recipient: str, data: bytes):
        bridgeMessage = BridgeMessage.decode(data)
        self._receiveBridge(bridgeMessage.container, token, amount)

class BridgeSupport:
    whitelistedBridgeAdapters: dict[BridgeAdapter, bool]

    def set(self, bridgeAdapter: BridgeAdapter, is_whitelisted: bool):
        self.whitelistedBridgeAdapters[bridgeAdapter] = is_whitelisted

    def _validate_bridge_adapter(self, bridge_adapter: BridgeAdapter):
        if bridge_adapter not in self.whitelistedBridgeAdapters:
            raise ValueError("Bridge adapter is not whitelisted")
