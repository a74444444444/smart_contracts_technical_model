# Deposit flow

1. Users call `vault.create_deposit_request(amount)`
2. Operator calls `vault.start_current_deposit_batch_processing()`
3. Operator calls start enter in all principals
```
for container in principals:
    operator call `container.start_enter(swaps, bridge_adapters, bridges)`
```
4. After bridges received on remote chain - liquidity stuck on bridge adapters. 
```
for ba in bridge_adapters:
    for token in awaitable tokens:
        agent.claim_bridge(ba, token)
``` 
5. After claimed liquidity stores on container, need to process liquidity preparation
```agent.prepare_liquidity(swaps)```
6.
```
for logic in agent.logics:
    agent.enter_logic(logic, tokens, tokenInAmounts, min_liquidity_delta)
```
7. Optional: if some enters failed - required to process exits
```
for logic in agent.logics:
    agent.exit_logic(logic)
```
8. By operator: `agent.finalize_remote_enter(bridge_adapters, bridges)`
9. By operator on principal: `principal.receive_message(deposit_confirmation)`
10. By operator: `principal.finalize_enter`
11. By operator: `vault.finish_deposit_batch_processing`
12. By user: `vault.claim_shares_after_deposit` or `vault.claim_remainder_after_deposit`

# Withdrawal flow
1. Users call `vault.create_withdrawal_request(shares_amount)`
2. Operator call `vault.start_current_withdrawal_batch_processing`
3. For each container on L2:
```
for agent in vault.containers:
    for logic in agent.logics:
        agent.exit_logic(logic, expected_tokens, min_tokens_delta)
```
4. For each agent:
```
for agent in vault.containers:
    agent.finish_withdrawal_processing()
```
