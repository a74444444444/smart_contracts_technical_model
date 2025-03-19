from swap_router import SwapRouter
from vault import Vault
from containers import Container
from datastructures import ERC20

# Deposit into empty vault

notion = ERC20(address="0x01", name="USDC")

swap_router = SwapRouter()

c1 = Container(
    swap_router=swap_router,
    notion=notion,
)
c2 = Container(
    swap_router=swap_router,
    notion=notion,
)
c3 = Container(
    swap_router=swap_router,
    notion=notion,
)
c4 = Container(
    swap_router=swap_router,
    notion=notion,
)
v = Vault(notion)
v.add_container(c1, 250)
v.add_container(c2, 250)
v.add_container(c3, 250)
v.add_container(c4, 250)

# process enter
print('Batch 1 with deposits 1-4 processing')
v.create_deposit_request(100)
v.create_deposit_request(100)
v.create_deposit_request(100)
v.create_deposit_request(100)

assert v.deposit_batch.buffered_amount == 400
print("Batch 1 processing...")
v.start_current_deposit_batch_processing()

assert v.deposit_batch.buffered_amount == 0
assert v.deposit_batch.id_ == 1
assert v.pending_deposit_batch.id == 0
assert v.pending_deposit_batch.batch_nav == 400

awaited_nav_after_harvest_and_enter_c1 = 95
awaited_nav_after_harvest_and_enter_c2 = 100
awaited_nav_after_harvest_and_enter_c3 = 95
awaited_nav_after_harvest_and_enter_c4 = 95

awaited_nav_after_harvest_c1 = awaited_nav_after_harvest_c2 = awaited_nav_after_harvest_c3 = awaited_nav_after_harvest_c4 = 0
awaited_notion_remainder_c1 = awaited_notion_remainder_c2 = awaited_notion_remainder_c3 = awaited_notion_remainder_c4 = 0

awaited_notion_growth = sum([
    awaited_nav_after_harvest_and_enter_c1 +
    awaited_nav_after_harvest_and_enter_c2 +
    awaited_nav_after_harvest_and_enter_c3 +
    awaited_nav_after_harvest_and_enter_c4
])

# как будто контейнер вернул коллбек
v.deposit_container_callback( # success enter into container 1
    nav_after_harvest=awaited_nav_after_harvest_c1,
    nav_after_harvest_and_enter=awaited_nav_after_harvest_and_enter_c1,
    notion_token_remainder=awaited_notion_remainder_c1,
)
v.deposit_container_callback( # success enter into container 2
    nav_after_harvest=awaited_nav_after_harvest_c1,
    nav_after_harvest_and_enter=awaited_nav_after_harvest_and_enter_c2,
    notion_token_remainder=awaited_notion_remainder_c1,
)
v.deposit_container_callback( # success enter into container 3
    nav_after_harvest=awaited_nav_after_harvest_c1,
    nav_after_harvest_and_enter=awaited_nav_after_harvest_and_enter_c3,
    notion_token_remainder=awaited_notion_remainder_c1,
)
v.deposit_container_callback( # success enter into container 4
    nav_after_harvest=awaited_nav_after_harvest_c1,
    nav_after_harvest_and_enter=awaited_nav_after_harvest_and_enter_c4,
    notion_token_remainder=awaited_notion_remainder_c1,
)

assert v.pending_deposit_batch.id == 0

v.finish_deposit_batch_processing()

assert v.total_shares == awaited_notion_growth
assert v.nav == awaited_notion_growth
print("Vault NAV: ", v.nav)
print("Total shares: ", v.total_shares)

v.claim_shares_after_deposit(0)
v.claim_shares_after_deposit(1)
v.claim_shares_after_deposit(2)
v.claim_shares_after_deposit(3)

print('User 1 claim shares: ', v.positions[0].shares_amount)
print('User 2 claim shares: ', v.positions[1].shares_amount)
print('User 3 claim shares: ', v.positions[2].shares_amount)
print('User 4 claim shares: ', v.positions[3].shares_amount)

claimed_shares = v.positions[0].shares_amount + v.positions[1].shares_amount + v.positions[2].shares_amount + v.positions[3].shares_amount

assert claimed_shares == v.total_shares - 1 # check effects of rounding

print("Batch 2 with deposits 5-7 processing")
v.create_deposit_request(300)
v.create_deposit_request(300)
v.create_deposit_request(200)

print("Batch 2 processing...")
v.start_current_deposit_batch_processing()


rewards_c1 = 5
rewards_c2 = 5
rewards_c3 = 5
rewards_c4 = 5

awaited_nav_after_harvest_c1 = awaited_nav_after_harvest_and_enter_c1 + rewards_c1
awaited_nav_after_harvest_c2 = awaited_nav_after_harvest_and_enter_c2 + rewards_c2
awaited_nav_after_harvest_c3 = awaited_nav_after_harvest_and_enter_c3 + rewards_c3
awaited_nav_after_harvest_c4 = awaited_nav_after_harvest_and_enter_c4 + rewards_c4


awaited_nav_after_harvest_and_enter_c1 = awaited_nav_after_harvest_c1 + 195
awaited_nav_after_harvest_and_enter_c2 = awaited_nav_after_harvest_c2 + 200
awaited_nav_after_harvest_and_enter_c3 = awaited_nav_after_harvest_c3 + 190
awaited_nav_after_harvest_and_enter_c4 = awaited_nav_after_harvest_c4 + 200

awaited_notion_remainder_c1 = awaited_notion_remainder_c2 = awaited_notion_remainder_c3 = awaited_notion_remainder_c4 = 0

awaited_notion_growth = sum([
    awaited_nav_after_harvest_and_enter_c1 +
    awaited_nav_after_harvest_and_enter_c2 +
    awaited_nav_after_harvest_and_enter_c3 +
    awaited_nav_after_harvest_and_enter_c4
])

# как будто контейнер вернул коллбек
v.deposit_container_callback( # success enter into container 1
    nav_after_harvest=awaited_nav_after_harvest_c1,
    nav_after_harvest_and_enter=awaited_nav_after_harvest_and_enter_c1,
    notion_token_remainder=awaited_notion_remainder_c1,
)
v.deposit_container_callback( # success enter into container 2
    nav_after_harvest=awaited_nav_after_harvest_c2,
    nav_after_harvest_and_enter=awaited_nav_after_harvest_and_enter_c2,
    notion_token_remainder=awaited_notion_remainder_c2,
)
v.deposit_container_callback( # success enter into container 3
    nav_after_harvest=awaited_nav_after_harvest_c3,
    nav_after_harvest_and_enter=awaited_nav_after_harvest_and_enter_c3,
    notion_token_remainder=awaited_notion_remainder_c3,
)
v.deposit_container_callback( # success enter into container 4
    nav_after_harvest=awaited_nav_after_harvest_c4,
    nav_after_harvest_and_enter=awaited_nav_after_harvest_and_enter_c4,
    notion_token_remainder=awaited_notion_remainder_c4,
)

v.finish_deposit_batch_processing()

print("Vault NAV: ", v.nav)
print("Total shares: ", v.total_shares)

v.claim_shares_after_deposit(4)
v.claim_shares_after_deposit(5)
v.claim_shares_after_deposit(6)

print('User 5 claim shares: ', v.positions[4].shares_amount)
print('User 6 claim shares: ', v.positions[5].shares_amount)
print('User 7 claim shares: ', v.positions[6].shares_amount)
