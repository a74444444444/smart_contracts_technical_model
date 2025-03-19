from vault import Vault
from containers import Container
from datastructures import ERC20, DepositConfirmation, SuccessDepositConfirmation

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

v.create_deposit_request(100)
v.create_deposit_request(100)
v.create_deposit_request(100)
v.create_deposit_request(100)

v.start_current_deposit_batch_processing()

v.deposit_container_callback(
    deposit_confirmation=SuccessDepositConfirmation(
        nav_growth=100,
        notion_token_remainder=0
    )
)
v.deposit_container_callback(
    deposit_confirmation=SuccessDepositConfirmation(
        nav_growth=90,
        notion_token_remainder=0
    )
)
v.deposit_container_callback(
    deposit_confirmation=SuccessDepositConfirmation(
        nav_growth=95,
        notion_token_remainder=0
    )
)
v.deposit_container_callback(
    deposit_confirmation=SuccessDepositConfirmation(
        nav_growth=100,
        notion_token_remainder=0
    )
)

v.finish_deposit_batch_processing()
v.claim_shares_after_deposit(0)
v.claim_shares_after_deposit(1)
v.claim_shares_after_deposit(2)
v.claim_shares_after_deposit(3)

# start full withdrawal processing by 2 users
user_0_total_shares = v.positions[0].shares_amount
user_1_total_shares = v.positions[1].shares_amount

v.create_withdrawal_request(0, user_0_total_shares)
v.create_withdrawal_request(1, user_1_total_shares)

v.start_current_withdrawal_batch_processing()

v.withdrawal_container_callback(notion_growth=50)
v.withdrawal_container_callback(notion_growth=45)
v.withdrawal_container_callback(notion_growth=47)
v.withdrawal_container_callback(notion_growth=50)

v.finish_withdrawal_batch_processing()

claimed_by_0 = v.claim_withdrawn_notion_token(0, 0)
claimed_by_1 = v.claim_withdrawn_notion_token(1, 0)
assert claimed_by_0 > 0
assert claimed_by_1 > 0