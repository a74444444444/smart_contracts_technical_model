from containers import PrincipalContainer, AgentContainer, Logic
from bridge_adapters import AcrossBridgeAdapter, CCTPBridgeAdapter
from datastructures import BridgeInstruction, ERC20, SwapInstruction, ContainerMessage, MessageType
from swap_router import SwapRouter
from vault import Vault
from eth_abi import encode

usdc = ERC20(address="0x01", name="USDC")
usdt = ERC20(address="0x02", name="USDT")

usdc_on_l2 = ERC20(address="0x03", name="USDC")
usdt_on_l2 = ERC20(address="0x04", name="USDT")

swap_router = SwapRouter()
principal_ba1 = AcrossBridgeAdapter()
agent_ba1 = AcrossBridgeAdapter()
principal_ba2 = CCTPBridgeAdapter()
agent_ba2 = CCTPBridgeAdapter()

principal = PrincipalContainer(
    vault=Vault(usdc),
    swap_router=swap_router,
    notion=usdc,
)
logic_1 = Logic()
logic_2 = Logic()

agent = AgentContainer(swap_router=swap_router, notion=usdc_on_l2)
agent.setLogic(logic_1, True)
agent.setLogic(logic_2, True)

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

# receive bridges on l2:
agent_ba1.handleV3AcrossMessage(
    token=usdt_on_l2.address,
    amount=25,
    recipient="0x",
    data=encode(["address"], [principal.address])
)
agent_ba2.cctpReceiveMessage(
    token=usdc_on_l2.address,
    amount=75,
    recipient="0x",
    data=encode(["address"], [principal.address])
)

agent.claim_bridge(agent_ba1, token=usdt_on_l2.address)
agent.claim_bridge(agent_ba2, token=usdc_on_l2.address)

agent.enter_logic(
    logic_1,
    [usdc_on_l2, usdt_on_l2],
    [25, 25],
    48
)
agent.enter_logic(
    logic_2,
    [usdc_on_l2],
    [50],
    48
)


# if success enters
agent.finalize_success_enters()
print('Container NAV after harvest: ', agent.last_message.nav_after_harvest)
print('Container NAV after harvest and enter: ', agent.last_message.nav_after_harvest_and_enter)

principal.receive_message(
    ContainerMessage(
        type=MessageType.DEPOSIT_CONFIRMATION,
        data=agent.last_message.to_bytes(),
    ).to_bytes()
)
principal.finalize_enter([], [])