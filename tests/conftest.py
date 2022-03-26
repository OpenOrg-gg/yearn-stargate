import pytest
from brownie import config
from brownie import Contract


@pytest.fixture
def gov(accounts):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)


@pytest.fixture
def user(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def management(accounts):
    yield accounts[3]


@pytest.fixture
def strategist(accounts):
    yield accounts[4]


@pytest.fixture
def keeper(accounts):
    yield accounts[5]


@pytest.fixture
def token():
    token_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # this should be the address of the ERC-20 used by the strategy/vault (USDC)
    yield Contract(token_address)

@pytest.fixture
def token2():
    token_address = "0xdac17f958d2ee523a2206206994597c13d831ec7"  # this should be the address of the ERC-20 used by the strategy/vault (USDT)
    yield Contract(token_address)

@pytest.fixture
def token_whale(accounts):
    yield accounts.at("0x7abe0ce388281d2acf297cb089caef3819b13448", force=True)

@pytest.fixture
def token2_whale(accounts):
    yield accounts.at("0xd6216fc19db775df9774a6e33526131da7d19a2c", force=True)

@pytest.fixture
def stg_token():
    token_address = "0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6"
    yield Contract(token_address)


@pytest.fixture
def lp_staker():
    address = "0xB0D502E938ed5f4df2E681fE6E419ff29631d62b"
    yield Contract(address)


@pytest.fixture
def stargate_router():
    address = "0x8731d54E9D02c286767d56ac03e8037C07e01e98"
    yield Contract(address)

@pytest.fixture
def trade_factory():
    yield Contract("0x99d8679bE15011dEAD893EB4F5df474a4e6a8b29")

@pytest.fixture
def curvePool():
    yield Contract("0x3211C6cBeF1429da3D0d58494938299C92Ad5860")

@pytest.fixture
def ymechs_safe():
    yield Contract("0x2C01B4AD51a67E2d8F02208F54dF9aC4c0B778B6")

@pytest.fixture
def stargate_token_pool():
    address = "0xdf0770dF86a8034b3EFEf0A1Bb3c889B8332FF56"  # for USDC
    yield Contract(address)

@pytest.fixture(scope="module")
def sushiswap_router(Contract):
    yield Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")

@pytest.fixture(scope="module")
def multicall_swapper(interface):
    yield interface.MultiCallOptimizedSwapper(
        "0xB2F65F254Ab636C96fb785cc9B4485cbeD39CDAA"
    )

@pytest.fixture(scope="session")
def liquidity_pool_id_in_lp_staking():
    yield 0

@pytest.fixture
def SGT_whale(accounts):
    yield accounts.at("0x485544e6fbef56d5bff61632b519ba0debdf28c1", force=True)

@pytest.fixture
def amount(accounts, token, user):
    amount = 100_000 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    reserve = accounts.at("0x7abe0ce388281d2acf297cb089caef3819b13448", force=True)
    token.transfer(user, amount, {"from": reserve})
    yield amount


@pytest.fixture
def univ3_swapper():
    address = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    yield Contract(address)

@pytest.fixture
def weth():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    yield Contract(token_address)


@pytest.fixture
def weth_amout(user, weth):
    weth_amout = 10 ** weth.decimals()
    user.transfer(weth, weth_amout)
    yield weth_amout


@pytest.fixture
def vault(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault

@pytest.fixture
def vault2(pm, gov, rewards, guardian, management, token2):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token2, gov, rewards, "", "", guardian, management)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def strategy(
    strategist, keeper, vault, Strategy, gov, lp_staker, liquidity_pool_id_in_lp_staking, weth, univ3_swapper, curvePool
):
    strategy = strategist.deploy(
        Strategy,
        vault,
        lp_staker,
        liquidity_pool_id_in_lp_staking,
        univ3_swapper,
        curvePool,
        "StrategyStargateUSDC",
    )
    strategy.setKeeper(keeper)
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    yield strategy


@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    yield 1e-5
