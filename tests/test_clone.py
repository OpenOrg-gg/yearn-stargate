import pytest

from brownie import chain, Wei, reverts, Contract

def test_double_init_should_revert(
    strategy,
    factory,
    vault,
    strategist,
    token,
    lp_staker,
    liquidity_pool_id_in_lp_staking,
    univ3_swapper,
    gov,
    keeper,
    rewards
):
    clone_tx = strategy.clone(
        vault,
        strategist,
        rewards,
        keeper,
        lp_staker,
        liquidity_pool_id_in_lp_staking,
        univ3_swapper,
        "ClonedStrategy",
        {"from": strategist},
    )

    cloned_strategy = Contract.from_abi(
        "Strategy", clone_tx.events["Cloned"]["clone"], strategy.abi
    )

    with reverts():
        strategy.initialize(
            vault,
            strategist,
            rewards,
            keeper,
            lp_staker,
            liquidity_pool_id_in_lp_staking,
            univ3_swapper,
            "RevertedStrat",
            {"from": gov}
        )

    with reverts():
        cloned_strategy.initialize(
            vault,
            strategist,
            rewards,
            keeper,
            lp_staker,
            liquidity_pool_id_in_lp_staking,
            univ3_swapper,
            "ClonedRevertedStrat",
            {"from": gov}
        )


def test_clone(
    strategy,
    factory,
    vault,
    strategist,
    token,
    lp_staker,
    liquidity_pool_id_in_lp_staking,
    univ3_swapper,
    gov,
    keeper,
    rewards,
    token_whale
):
    clone_tx = factory.cloneMIMMinter(
        vault,
        strategist,
        rewards,
        keeper,
        lp_staker,
        liquidity_pool_id_in_lp_staking,
        univ3_swapper,
        "ClonedStrategy",
        {"from": strategist},
    )

    cloned_strategy = Contract.from_abi(
        "Strategy", clone_tx.events["Cloned"]["clone"], strategy.abi
    )

    vault.updateStrategyDebtRatio(strategy, 0, {"from": gov})
    vault.addStrategy(cloned_strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(10 * (10 ** token.decimals()), {"from": token_whale})

    chain.sleep(1)
    cloned_strategy.harvest({"from": gov})

    # Sleep for 2 days
    chain.sleep(60 * 60 * 24 * 2)
    chain.mine(1)

    cloned_strategy.harvest({"from": gov})

    assert vault.strategies(cloned_strategy).dict()["totalGain"] > 0
    assert vault.strategies(cloned_strategy).dict()["totalLoss"] == 0
