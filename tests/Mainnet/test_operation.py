import brownie
from brownie import Contract, ZERO_ADDRESS
import pytest


def test_operation(
    chain, accounts, token, vault, strategy, user, strategist, amount, RELATIVE_APPROX, gov
):
    # Deposit to the vault
    user_balance_before = token.balanceOf(user)
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # tend()
    tx = strategy.tend()
    tx.wait(1)

    # withdrawal
    vault.withdraw({"from": user})
    assert (
        pytest.approx(token.balanceOf(user), rel=RELATIVE_APPROX) == user_balance_before
    )


def test_change_debt(
    chain, gov, token, vault, strategy, user, strategist, amount, RELATIVE_APPROX
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    half = int(amount / 2)

    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == half

    vault.updateStrategyDebtRatio(strategy.address, 10_000, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # In order to pass this tests, you will need to implement prepareReturn.
    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == half


def test_sweep(gov, vault, strategy, token, user, amount, weth):
    # Strategy want token doesn't work
    token.transfer(strategy, amount, {"from": user})
    assert token.address == strategy.want()
    assert token.balanceOf(strategy) > 0
    with brownie.reverts("!want"):
        strategy.sweep(token, {"from": gov})

    # Vault share token doesn't work
    with brownie.reverts("!shares"):
        strategy.sweep(vault.address, {"from": gov})

    # TODO: If you add protected tokens to the strategy.
    # Protected token doesn't work
    # with brownie.reverts("!protected"):
    #     strategy.sweep(strategy.protectedToken(), {"from": gov})

def test_triggers(
    chain, gov, vault, strategy, token, amount, user, weth, strategist
):
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    chain.sleep(1)
    strategy.harvest({"from": gov})
    strategy.harvestTrigger(0)
    strategy.tendTrigger(0)


def test_losses(
    chain,
    accounts,
    token,
    vault,
    strategy,
    user,
    strategist,
    amount,
    RELATIVE_APPROX,
    lp_staker,
    stargate_token_pool,
    keeper,
    gov
):
    # Deposit to the vault
    user_balance_before = token.balanceOf(user)
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    strategy.setDoHealthCheck(False, {"from": gov})
    # harvest
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    # tend()
    tx = strategy.tend()
    tx.wait(1)

    # simulate getting rekt
    strategy_account = accounts.at(strategy.address, force=True)

    lp_staker.emergencyWithdraw(
        strategy.liquidityPoolIDInLPStaking(), {"from": strategy_account}
    )
    stargate_token_pool.transfer(
        ZERO_ADDRESS,
        stargate_token_pool.balanceOf(strategy),
        {"from": strategy_account},
    )

    chain.sleep(1)
    tx = strategy.harvest({"from": gov})

    assert (
        pytest.approx(tx.events["StrategyReported"]["loss"], rel=RELATIVE_APPROX)
        == amount
    )

    # withdrawal
    vault.withdraw({"from": user})
    assert (
        pytest.approx(token.balanceOf(user), rel=RELATIVE_APPROX)
        == user_balance_before - amount
    )

def test_equal_distribution_of_losses_2_percent_loss(
    chain,
    accounts,
    token,
    vault,
    strategy,
    user,
    strategist,
    amount,
    RELATIVE_APPROX,
    lp_staker,
    stargate_token_pool,
    keeper,
    gov,
    amount2,
    user2,
    userBIG,
    amountBIG
):
    strategy.setDoHealthCheck(False, {"from": gov})
    # Deposit to the vault
    user_balance_before = token.balanceOf(user)
    user2_balance_before = token.balanceOf(user2)
    token.approve(vault.address, amount, {"from": user})
    token.approve(vault.address, amount2, {"from": user2})
    token.approve(vault.address, amountBIG, {"from": userBIG})
    vault.deposit(amount, {"from": user})
    vault.deposit(amount2, {"from": user2})
    vault.deposit(amountBIG, {"from": userBIG})
    assert token.balanceOf(vault.address) == amount + amount2 + amountBIG
    token.transfer(gov, token.balanceOf(user), {"from": user})
    token.transfer(gov, token.balanceOf(user2), {"from": user2})
    token.transfer(gov, token.balanceOf(userBIG), {"from": userBIG})

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount + amount2 + amountBIG

    # tend()
    tx = strategy.tend()
    tx.wait(1)

    # simulate getting rekt
    strategy_account = accounts.at(strategy.address, force=True)

    lp_staker.emergencyWithdraw(strategy.liquidityPoolIDInLPStaking(), {"from": strategy_account})
    #lose 2% of tokens
    loss_percentage = 0.02
    stargate_token_pool.transfer(ZERO_ADDRESS, stargate_token_pool.balanceOf(strategy)*loss_percentage, {"from": strategy_account},)

    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    assert (pytest.approx(tx.events["StrategyReported"]["loss"], rel=RELATIVE_APPROX) == (amount+amount2+amountBIG)*loss_percentage)

    # withdrawal
    vault.withdraw({"from": user})
    vault.withdraw({"from": userBIG})
    vault.withdraw({"from": user2})
    assert (pytest.approx(token.balanceOf(user)+(vault.balanceOf(user)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == token.balanceOf(user2)+(vault.balanceOf(user2)*vault.pricePerShare()/(10**token.decimals())))
    assert (pytest.approx(token.balanceOf(user)+(vault.balanceOf(user)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == amount * (1-loss_percentage))
    assert (pytest.approx(token.balanceOf(user2)+(vault.balanceOf(user2)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == amount2 * (1-loss_percentage))
    assert (pytest.approx(token.balanceOf(userBIG)+(vault.balanceOf(userBIG)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == amountBIG * (1-loss_percentage))



def test_equal_distribution_of_losses_30_percent_loss(
    chain,
    accounts,
    token,
    vault,
    strategy,
    user,
    strategist,
    amount,
    RELATIVE_APPROX,
    lp_staker,
    stargate_token_pool,
    keeper,
    gov,
    amount2,
    user2,
    userBIG,
    amountBIG
):
    strategy.setDoHealthCheck(False, {"from": gov})
    # Deposit to the vault
    user_balance_before = token.balanceOf(user)
    user2_balance_before = token.balanceOf(user2)
    token.approve(vault.address, amount, {"from": user})
    token.approve(vault.address, amount2, {"from": user2})
    token.approve(vault.address, amountBIG, {"from": userBIG})
    vault.deposit(amount, {"from": user})
    vault.deposit(amount2, {"from": user2})
    vault.deposit(amountBIG, {"from": userBIG})
    assert token.balanceOf(vault.address) == amount + amount2 + amountBIG
    token.transfer(gov, token.balanceOf(user), {"from": user})
    token.transfer(gov, token.balanceOf(user2), {"from": user2})
    token.transfer(gov, token.balanceOf(userBIG), {"from": userBIG})

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount + amount2 + amountBIG

    # tend()
    tx = strategy.tend()
    tx.wait(1)

    # simulate getting rekt
    strategy_account = accounts.at(strategy.address, force=True)

    lp_staker.emergencyWithdraw(strategy.liquidityPoolIDInLPStaking(), {"from": strategy_account})
    #lose 30% of tokens
    loss_percentage = 0.3
    stargate_token_pool.transfer(ZERO_ADDRESS, stargate_token_pool.balanceOf(strategy)*loss_percentage, {"from": strategy_account},)

    chain.sleep(1)
    tx = strategy.harvest({"from": gov})

    assert (pytest.approx(tx.events["StrategyReported"]["loss"], rel=RELATIVE_APPROX) == (amount+amount2+amountBIG)*loss_percentage)

    # withdrawal
    vault.withdraw({"from": user})
    vault.withdraw({"from": userBIG})
    vault.withdraw({"from": user2})
    assert (pytest.approx(token.balanceOf(user)+(vault.balanceOf(user)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == token.balanceOf(user2)+(vault.balanceOf(user2)*vault.pricePerShare()/(10**token.decimals())))
    assert (pytest.approx(token.balanceOf(user)+(vault.balanceOf(user)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == amount * (1-loss_percentage))
    assert (pytest.approx(token.balanceOf(user2)+(vault.balanceOf(user2)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == amount2 * (1-loss_percentage))
    assert (pytest.approx(token.balanceOf(userBIG)+(vault.balanceOf(userBIG)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == amountBIG * (1-loss_percentage))


def test_equal_distribution_of_losses_100_percent_loss(
    chain,
    accounts,
    token,
    vault,
    strategy,
    user,
    strategist,
    amount,
    RELATIVE_APPROX,
    lp_staker,
    stargate_token_pool,
    keeper,
    gov,
    amount2,
    user2,
    userBIG,
    amountBIG
):
    strategy.setDoHealthCheck(False, {"from": gov})
    # Deposit to the vault
    user_balance_before = token.balanceOf(user)
    user2_balance_before = token.balanceOf(user2)
    token.approve(vault.address, amount, {"from": user})
    token.approve(vault.address, amount2, {"from": user2})
    token.approve(vault.address, amountBIG, {"from": userBIG})
    vault.deposit(amount, {"from": user})
    vault.deposit(amount2, {"from": user2})
    vault.deposit(amountBIG, {"from": userBIG})
    assert token.balanceOf(vault.address) == amount + amount2 + amountBIG
    token.transfer(gov, token.balanceOf(user), {"from": user})
    token.transfer(gov, token.balanceOf(user2), {"from": user2})
    token.transfer(gov, token.balanceOf(userBIG), {"from": userBIG})

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount + amount2 + amountBIG

    # tend()
    tx = strategy.tend()
    tx.wait(1)

    # simulate getting rekt
    strategy_account = accounts.at(strategy.address, force=True)

    lp_staker.emergencyWithdraw(strategy.liquidityPoolIDInLPStaking(), {"from": strategy_account})
    #lose 100% of tokens
    loss_percentage = 1
    stargate_token_pool.transfer(ZERO_ADDRESS, stargate_token_pool.balanceOf(strategy)*loss_percentage, {"from": strategy_account},)

    chain.sleep(1)
    tx = strategy.harvest({"from": gov})

    assert (pytest.approx(tx.events["StrategyReported"]["loss"], rel=RELATIVE_APPROX) == (amount+amount2+amountBIG)*loss_percentage)

    # withdrawal
    vault.withdraw({"from": user})
    vault.withdraw({"from": userBIG})
    vault.withdraw({"from": user2})
    assert (pytest.approx(token.balanceOf(user)+(vault.balanceOf(user)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == token.balanceOf(user2)+(vault.balanceOf(user2)*vault.pricePerShare()/(10**token.decimals())))
    assert (pytest.approx(token.balanceOf(user)+(vault.balanceOf(user)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == amount * (1-loss_percentage))
    assert (pytest.approx(token.balanceOf(user2)+(vault.balanceOf(user2)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == amount2 * (1-loss_percentage))
    assert (pytest.approx(token.balanceOf(userBIG)+(vault.balanceOf(userBIG)*vault.pricePerShare()/(10**token.decimals())), rel=RELATIVE_APPROX) == amountBIG * (1-loss_percentage))


def test_limited_delta_credit_no_loss(
    chain, accounts, token, vault, strategy, user, strategist, amount, RELATIVE_APPROX, gov, token_LP_whale,
):
    # Deposit to the vault
    user_balance_before = token.balanceOf(user)
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount
    strategy.setDoHealthCheck(False, {"from": gov})

    # harvest
    chain.sleep(1)
    strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    liquidityPool = Contract(strategy.liquidityPool())
    router = Contract(liquidityPool.router())
    router.instantRedeemLocal(liquidityPool.poolId(), liquidityPool.deltaCredit(), strategist, {"from":token_LP_whale})

    assert liquidityPool.deltaCredit() < amount
    vault.updateStrategyDebtRatio(strategy.address, 0, {"from": gov})
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount
    assert tx.events['StrategyReported']['loss'] < 10 #might have a small loss due to rounding error
    assert pytest.approx(vault.debtOutstanding(strategy), rel=RELATIVE_APPROX) == amount
