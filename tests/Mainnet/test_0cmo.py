import brownie
import pytest
from brownie import chain, Wei, reverts, Contract
import eth_utils
from eth_abi import encode_single, encode_abi
from brownie.convert import to_bytes
from eth_abi.packed import encode_abi_packed

def test_migrate_stargate(chain,
    accounts,
    amount,
    RELATIVE_APPROX,
    stg_token,
    curve_pool,
    univ2_router,
    multicall_swapper,
    usdc,
    weth,
    ymechs_safe,
    trade_factory,
    wantIsWeth,
    emissionTokenIsSTG,
    lp_staker,
    strategist, Strategy):
    # Contracts
    sms = Contract("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7")
    ychad = Contract("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52")

    old_stargate_usdc = Contract("0x7C85c0a8E2a45EefF98A10b6037f70daf714B7cf")
    old_stargate_usdt = Contract("0xeAD650E673F497CdBE365F7a855273BbB468e454")
    old_stargates = [old_stargate_usdc, old_stargate_usdt]

    usdc_vault = Contract(old_stargate_usdc.vault())
    usdt_vault = Contract(old_stargate_usdt.vault())
    safe = Contract(usdc_vault.governance())

    new_stargate_usdc = strategist.deploy(Strategy, usdc_vault, lp_staker, 0, False, True, "StargateV2-USDC")
    new_stargate_usdc.setRewards("0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde", {"from": strategist})
    new_stargate_usdc.setStrategist(sms, {"from": strategist})
    new_stargate_usdt = strategist.deploy(Strategy, usdt_vault, lp_staker, 1, False, True, "StargateV2-USDC")
    new_stargate_usdt.setRewards("0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde", {"from": strategist})
    new_stargate_usdt.setStrategist(sms, {"from": strategist})

    #new_stargate_usdc = Contract("0x11E57D1520997c42C05bC35B8b083Be22Ab911c0")
    #new_stargate_usdt = Contract("0xF4A5dcBaFa166caC0A1c8d293f92128308831880")
    new_stargates = [new_stargate_usdc, new_stargate_usdt]

    usdc_assets_before = usdc_vault.strategies(old_stargate_usdc)['totalDebt']
    usdt_assets_before = usdt_vault.strategies(old_stargate_usdt)['totalDebt'] 

    stg = Contract("0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6")
    susdc = Contract("0xdf0770dF86a8034b3EFEf0A1Bb3c889B8332FF56")

    # step 1 - claim STG rewards and sweep
    old_stargate_usdc.claimRewards({"from": safe})       
    stg_stargate_usdc = old_stargate_usdc.balanceOfSTG()
    old_stargate_usdc.sweep(stg, {"from": safe})
    assert old_stargate_usdc.balanceOfSTG() == 0
    old_stargate_usdt.claimRewards({"from": safe})       
    stg_stargate_usdt = old_stargate_usdt.balanceOfSTG()
    old_stargate_usdt.sweep(stg, {"from": safe})
    assert old_stargate_usdt.balanceOfSTG() == 0

    # step 2 - migrate strategies
    usdc_vault.migrateStrategy(old_stargate_usdc, new_stargate_usdc, {"from": safe})
    usdt_vault.migrateStrategy(old_stargate_usdt, new_stargate_usdt, {"from": safe})

    # step 3 - sweep all S*USDC to ychad
    new_stargate_usdc.sweep(susdc, {"from": safe}) # sweep all S*USDC to ychad

    # step 4 - reimburse SMS for 223_490e6 USDC equivalent, then airdrop the diff to strategy
    lp_amount = 223330500465 # calculated via tenderly simul
    susdc.transfer(sms, lp_amount, {"from": safe}) # send S*USDC to SMS
    remaining_sudc_balance = susdc.balanceOf(ychad)
    susdc.transfer(new_stargate_usdc, remaining_sudc_balance, {"from": safe}) # send diff back to strategy

    assert new_stargate_usdc.estimatedTotalAssets() >= usdc_assets_before
    assert new_stargate_usdt.estimatedTotalAssets() >= usdt_assets_before 

    assert Contract(old_stargate_usdc.vault()) == Contract(new_stargate_usdc.vault())
    assert Contract(old_stargate_usdt.vault()) == Contract(new_stargate_usdt.vault())

    ############## send STG back to strategies:
    stg.transfer(new_stargate_usdc, stg_stargate_usdc, {"from": safe})
    stg.transfer(new_stargate_usdt, stg_stargate_usdt, {"from": safe})

    #Simple swap of STG rewards:
    amount_in = stg.balanceOf(new_stargate_usdc)
    stg.approve(curve_pool, amount_in, {"from": new_stargate_usdc})
    curve_pool.exchange(0, 1, amount_in, 0, {"from": new_stargate_usdc})
    assert stg.balanceOf(new_stargate_usdc) == 0

    chain.sleep(60)
    new_stargate_usdc.harvest({"from": safe})
    new_stargate_usdt.harvest({"from": safe})
    assert new_stargate_usdc.estimatedTotalAssets() >= usdc_assets_before
    assert new_stargate_usdt.estimatedTotalAssets() >= usdt_assets_before 


    """
    ######################## YSWAPS:
    for strategy in new_stargates:
        token_in = stg_token
        token_out = Contract(strategy.want())

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

        expected_out = (curve_pool.get_dy(0, 1, amount_in)  ) / 10_000

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


        ############# HARVEST:

        chain.sleep(60)
        chain.mine(1)
        tx = strategy.harvest({"from": safe})
        print(tx.events)
        assert tx.events["Harvested"]["profit"] > 0

        before_pps = Contract(strategy.vault()).pricePerShare()
        # Harvest 2: Realize profit
        chain.sleep(1)
        tx = strategy.harvest({"from": gov})
        chain.sleep(3600 * 6)  # 6 hrs needed for profits to unlock
        chain.mine(1)
        profit = token.balanceOf(Contract(strategy.vault()))  # Profits go to vault

        assert strategy.estimatedTotalAssets() + profit > amount
        assert Contract(strategy.vault()).pricePerShare() > before_pps
        assert stg_token.balanceOf(strategy) < 1e18  # dust is OK

    """


def createTx(to, data):
    inBytes = eth_utils.to_bytes(hexstr=data)
    return [["address", "uint256", "bytes"], [to.address, len(inBytes), inBytes]]
