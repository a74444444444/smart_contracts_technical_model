from vault import Vault
from containers import Container
from datastructures import ERC20, DepositConfirmation


notion = ERC20(address="0x01", name="USDC")

c1 = Container()
c2 = Container()
c3 = Container()
c4 = Container()
v = Vault(notion)
v.add_container(c1, 250)
v.add_container(c2, 250)
v.add_container(c3, 250)
v.add_container(c4, 250)

# process enter
v.create_deposit_request(100)
v.create_deposit_request(100)
v.create_deposit_request(100)
v.create_deposit_request(100)

v.start_current_deposit_batch_processing()

v.deposit_container_callback(
    deposit_confirmation=DepositConfirmation(
        nav_growth=100,
        notion_token_remainder=0
    )
)
v.deposit_container_callback(
    deposit_confirmation=DepositConfirmation(
        nav_growth=90,
        notion_token_remainder=0
    )
)
v.deposit_container_callback(
    deposit_confirmation=DepositConfirmation(
        nav_growth=95,
        notion_token_remainder=0
    )
)
v.deposit_container_callback(
    deposit_confirmation=DepositConfirmation(
        nav_growth=0,
        notion_token_remainder=100
    )
)

# should failed
try:
    v.finish_deposit_batch_processing()
except Exception as e:
    pass


# finish deposit container callback
v.deposit_container_callback(
    deposit_confirmation=DepositConfirmation(
        nav_growth=0,
        notion_token_remainder=100
    )
)
v.deposit_container_callback(
    deposit_confirmation=DepositConfirmation(
        nav_growth=0,
        notion_token_remainder=100
    )
)
v.deposit_container_callback(
    deposit_confirmation=DepositConfirmation(
        nav_growth=0,
        notion_token_remainder=95
    )
)
v.reset_pending_deposit_nav_growth()
v.finish_deposit_batch_processing()


claimed_by_0 = v.claim_remainder_after_deposit(0)
claimed_by_1 = v.claim_remainder_after_deposit(1)
claimed_by_2 = v.claim_remainder_after_deposit(2)
claimed_by_3 = v.claim_remainder_after_deposit(3)

assert v.positions[0].shares_amount == 0
assert v.positions[1].shares_amount == 0
assert v.positions[2].shares_amount == 0
assert v.positions[3].shares_amount == 0

assert v.positions[0].locked_shares_amount == 0
assert v.positions[1].locked_shares_amount == 0
assert v.positions[2].locked_shares_amount == 0
assert v.positions[3].locked_shares_amount == 0

assert claimed_by_0 == (100 + 100 + 100 + 95) // 4
assert claimed_by_1 == (100 + 100 + 100 + 95) // 4
assert claimed_by_2 == (100 + 100 + 100 + 95) // 4
assert claimed_by_3 == (100 + 100 + 100 + 95) // 4