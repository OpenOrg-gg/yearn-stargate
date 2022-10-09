from brownie import Contract, Wei
import brownie
from eth_abi import encode_single, encode_abi
from brownie.convert import to_bytes
from eth_abi.packed import encode_abi_packed
import pytest
import eth_utils


def test_profitable_harvest_curve(
    chain,
    accounts,
    token,
    vault,
    strategy,
    user,
    strategist,
    amount,
    RELATIVE_APPROX,
    stg_token,
    stg_whale,
    curve_pool,
    univ2_router,
    multicall_swapper,
    usdc,
    weth,
    ymechs_safe,
    trade_factory,
    gov,
    wantIsWeth
):
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": user})
    vault.deposit(amount, {"from": user})
    assert token.balanceOf(vault.address) == amount

    # Harvest 1: Send funds through the strategy
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    assert pytest.approx(strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    stg_token.transfer(strategy, 1_000e18, {"from": stg_whale})

    token_in = stg_token
    token_out = token

    print(f"Executing trade...")
    receiver = strategy.address
    amount_in = token_in.balanceOf(strategy)

    asyncTradeExecutionDetails = [strategy, token_in, token_out, amount_in, 1]

    # always start with optimizations. 5 is CallOnlyNoValue
    optimizations = [["uint8"], [5]]
    a = optimizations[0]
    b = optimizations[1]

    calldata = token_in.approve.encode_input(curve_pool, amount_in)
    t = createTx(token_in, calldata)
    a = a + t[0]
    b = b + t[1]

    expected_out = (curve_pool.get_dy(0, 1, amount_in) * 9_800) / 10_000

    calldata = curve_pool.exchange.encode_input(0, 1, amount_in, expected_out)
    t = createTx(curve_pool, calldata)
    a = a + t[0]
    b = b + t[1]

    if usdc != token_out:
        path = [usdc.address, weth.address, token_out.address]
        if weth == token and wantIsWeth == True:
            path = [usdc.address, token_out.address]

        calldata = usdc.approve.encode_input(univ2_router, 2 ** 256 - 1)
        t = createTx(usdc, calldata)
        a = a + t[0]
        b = b + t[1]

        # ?? seems like wrong amount_in:
        #calldata = univ2_router.swapExactTokensForTokens.encode_input(
        #    amount_in, 0, path, multicall_swapper, 2 ** 256 - 1
        #)

        # better:
        calldata = univ2_router.swapExactTokensForTokens.encode_input(expected_out, 0, path, multicall_swapper.address, 2 ** 256 - 1)

        t = createTx(univ2_router, calldata)
        a = a + t[0]
        b = b + t[1]

        if weth == token and wantIsWeth == True:
            expected_out = univ2_router.getAmountsOut(expected_out, path)[1]
        else:
            expected_out = univ2_router.getAmountsOut(expected_out, path)[2]

    calldata = token_out.transfer.encode_input(receiver, expected_out)
    t = createTx(token_out, calldata)
    a = a + t[0]
    b = b + t[1]

    transaction = encode_abi_packed(a, b)

    # min out must be at least 1 to ensure that the tx works correctly
    # trade_factory.execute["uint256, address, uint, bytes"](
    #    multicall_swapper.address, 1, transaction, {"from": ymechs_safe}
    # )
    trade_factory.execute["tuple,address,bytes"](
        asyncTradeExecutionDetails,
        multicall_swapper.address,
        transaction,
        {"from": ymechs_safe},
    )
    print(token_out.balanceOf(strategy))

    tx = strategy.harvest({"from": strategist})
    print(tx.events)
    assert tx.events["Harvested"]["profit"] > 0

    before_pps = vault.pricePerShare()
    # Harvest 2: Realize profit
    chain.sleep(1)
    tx = strategy.harvest({"from": gov})
    chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
    chain.mine(1)
    profit = token.balanceOf(vault.address)  # Profits go to vault

    assert strategy.estimatedTotalAssets() + profit > amount
    assert vault.pricePerShare() > before_pps
    assert stg_token.balanceOf(strategy) < 1e18  # dust is OK


def createTx(to, data):
    inBytes = eth_utils.to_bytes(hexstr=data)
    return [["address", "uint256", "bytes"], [to.address, len(inBytes), inBytes]]


def test_remove_trade_factory(strategy, gov, trade_factory, stg_token):
    assert strategy.tradeFactory() == trade_factory.address
    assert stg_token.allowance(strategy.address, trade_factory.address) > 0

    strategy.removeTradeFactoryPermissions({"from": gov})

    assert strategy.tradeFactory() != trade_factory.address
    assert stg_token.allowance(strategy.address, trade_factory.address) == 0
