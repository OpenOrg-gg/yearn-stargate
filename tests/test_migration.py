# TODO: Add tests that show proper migration of the strategy to a newer one
#       Use another copy of the strategy to simulate the migration
#       Show that nothing is lost!

import pytest


def test_migration(
    chain,
    token,
    vault,
    strategy,
    amount,
    Strategy,
    strategist,
    gov,
    user,
    RELATIVE_APPROX,
    lp_staker,
    liquidity_pool_id_in_lp_staking,
    curvePool,
    univ3_swapper,
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    chain.sleep(1)
    strategy.harvest()
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # migrate to a new strategy
    new_strategy = strategist.deploy(
        Strategy,
        vault,
        lp_staker,
        liquidity_pool_id_in_lp_staking,
        univ3_swapper,
        curvePool,
        "StrategyStargateUSDC",
    )
    previous_debt = vault.strategies(strategy).dict()["totalDebt"]
    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == 0
    assert (
        pytest.approx(new_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX)
        == amount
    )
    assert vault.strategies(new_strategy).dict()["totalDebt"] == previous_debt
