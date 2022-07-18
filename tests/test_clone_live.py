import pytest

from brownie import chain, Wei, reverts, Contract, accounts


def test_clone_for_usdt(
    gov,
    amount,
    RELATIVE_APPROX,
):
    token = Contract("0xdac17f958d2ee523a2206206994597c13d831ec7") #usdt
    token_whale = accounts.at("0x5a52e96bacdabb82fd05763e25335261b270efcb", force=True)
    vault = Contract("0x3B27F92C0e212C671EA351827EDF93DB27cc0c65") #usdt 043
    strategy = Contract("0x7c85c0a8e2a45eeff98a10b6037f70daf714b7cf") #usdc strategy which is clonable
    clone_tx = strategy.clone(
        "0x3B27F92C0e212C671EA351827EDF93DB27cc0c65",
        "0x16388463d60ffe0661cf7f1f31a7d658ac790ff7",
        "0x93a62da5a14c80f265dabc077fcee437b1a0efde",
        "0x736d7e3c5a6cb2ce3b764300140abf476f6cfccf",
        "0xB0D502E938ed5f4df2E681fE6E419ff29631d62b",
        1,
        "0xee9f2375b4bdf6387aa8265dd4fb8f16512a1d46",
        "StargateUSDTStaker",
        {"from": "0x16388463d60ffe0661cf7f1f31a7d658ac790ff7"},
    )

    cloned_strategy = Contract.from_abi(
        "Strategy", clone_tx.events["Cloned"]["clone"], strategy.abi
    )

    vault.acceptGovernance({"from": gov})
    vault.setDepositLimit(100_000_000e6,{"from": gov})
    vault.addStrategy(cloned_strategy, 10_000, 0, 2 ** 256 - 1, 0, {"from": gov})

    token.approve(vault, 2 ** 256 - 1, {"from": token_whale})
    vault.deposit(amount, {"from": token_whale})

    chain.sleep(1)
    cloned_strategy.harvest({"from": gov})

    assert pytest.approx(cloned_strategy.estimatedTotalAssets(), rel=RELATIVE_APPROX) == amount

    assert (
        vault.strategies(cloned_strategy).dict()["totalLoss"] < 10
    )  # might be a loss from rounding
