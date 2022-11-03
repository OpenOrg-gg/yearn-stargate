import brownie
from brownie import Contract, ZERO_ADDRESS
import pytest

def test_limited_delta_credit_profit(
    chain, accounts, token, vault, strategy, user, strategist, amount, RELATIVE_APPROX, gov, token_LP_whale, stargate_token_pool
):
    # 1- Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount
    strategy.setDoHealthCheck(False, {"from": gov})

    # 2- Harvest
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # 3- Simulate profit via want airdrop of S*token
    chain.sleep(1)
    whale = Contract("0xB0D502E938ed5f4df2E681fE6E419ff29631d62b")
    stargate_token_pool.transfer(strategy.address, amount, {"from": whale})

    # 4- Ensure that there is no sufficient deltaCredit
    liquidityPool = Contract(strategy.liquidityPool())
    router = Contract(liquidityPool.router())
    router.instantRedeemLocal(liquidityPool.poolId(), liquidityPool.deltaCredit(), strategist, {"from":token_LP_whale})

    # 5- Call another harvest and see if profit is repported correctly
    assert liquidityPool.deltaCredit() < amount
    vault.updateStrategyDebtRatio(strategy.address, 0, {"from": gov})
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
