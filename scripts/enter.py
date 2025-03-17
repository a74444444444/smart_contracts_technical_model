from typing import assert_type

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

assert v.deposit_batch.buffered_amount == 400
v.start_current_deposit_batch_processing()

assert v.deposit_batch.buffered_amount == 0
assert v.deposit_batch.id_ == 1
assert v.pending_deposit_batch.id == 0
assert v.pending_deposit_batch.batch_nav == 400

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
        nav_growth=100,
        notion_token_remainder=0
    )
)

notion_growth = 100 + 90 + 95 + 100
assert v.pending_deposit_batch.id == 0
assert v.pending_deposit_batch.nav_growth == notion_growth # see deposit_container_callback

v.finish_deposit_batch_processing()

assert v.total_shares == notion_growth
assert v.nav == notion_growth

v.claim_shares_after_deposit(0)
v.claim_shares_after_deposit(1)
v.claim_shares_after_deposit(2)
v.claim_shares_after_deposit(3)

claimed_shares = v.positions[0].shares_amount + v.positions[1].shares_amount + v.positions[2].shares_amount + v.positions[3].shares_amount

assert claimed_shares == v.total_shares - 1 # check effects of rounding