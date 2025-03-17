from containers import PrincipalContainer, AgentContainer
from bridge_adapters import BridgeAdapter
from datastructures import BridgeInstruction, ERC20, SwapInstruction
from swap_router import SwapRouter

usdc = ERC20(address="0x01", name="USDC")
usdt = ERC20(address="0x02", name="USDT")

swap_router = SwapRouter()
principal_ba1 = BridgeAdapter()
agent_ba1 = BridgeAdapter()
principal_ba2 = BridgeAdapter()
agent_ba2 = BridgeAdapter()

principal = PrincipalContainer(swap_router=swap_router)
agent = AgentContainer(swap_router=swap_router)

principal.start_enter(
    swaps=[
        SwapInstruction(
            token_in=usdc.address,
            token_out=usdt.address,
            amount_in=50,
            min_amount_out=50,
            payload=bytes()
        )
    ],
    bridge_adapters=[principal_ba1, principal_ba2],
    bridge_instructions=[
        BridgeInstruction(
            token=usdc.address,
            amount=50,
            payload=bytes()
        ),
        BridgeInstruction(
            token=usdt.address,
            amount=50,
            payload=bytes()
        )
    ]
)
