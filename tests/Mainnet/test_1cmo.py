import pytest
from brownie import chain, Wei, reverts, Contract

def test_migrate_stargate():
    # Contracts
    sms = Contract("0x16388463d60FFE0661Cf7F1f31a7D658aC790ff7")
    ychad = Contract("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52")

    old_stargate_usdc = Contract("0x7C85c0a8E2a45EefF98A10b6037f70daf714B7cf")
    old_stargate_usdt = Contract("0xeAD650E673F497CdBE365F7a855273BbB468e454")
    old_stargates = [old_stargate_usdc, old_stargate_usdt]

    new_stargate_usdc = Contract("0x11E57D1520997c42C05bC35B8b083Be22Ab911c0")
    new_stargate_usdt = Contract("0xF4A5dcBaFa166caC0A1c8d293f92128308831880")

    usdc_vault = Contract(old_stargate_usdc.vault())
    usdt_vault = Contract(old_stargate_usdt.vault())

    usdc_assets_before = usdc_vault.strategies(old_stargate_usdc)['totalDebt']
    usdt_assets_before = usdt_vault.strategies(old_stargate_usdt)['totalDebt'] 
    safe = Contract(usdc_vault.governance())

    stg = Contract("0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6")
    susdc = Contract("0xdf0770dF86a8034b3EFEf0A1Bb3c889B8332FF56")

    # step 1 - claim STG rewards and sweep
    for s in old_stargates:
        s.claimRewards({"from": safe})       
        s.sweep(stg, {"from": safe})
        assert s.balanceOfSTG() == 0

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

    chain.sleep(60)
    new_stargate_usdc.harvest({"from": safe})
    new_stargate_usdt.harvest({"from": safe})
    assert new_stargate_usdc.estimatedTotalAssets() >= usdc_assets_before
    assert new_stargate_usdt.estimatedTotalAssets() >= usdt_assets_before 

