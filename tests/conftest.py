import pytest
from brownie import config
from brownie import Contract

token_addresses = {
    "USDC": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH ! = 
}

token_id = {
    "USDC": 0,  # USDC
    "USDT": 1,  # USDT
    "WETH": 2,  # WETH ! = 
}

token_prices = {
    "WBTC": 35_000,
    "WETH": 2_000,
    "USDT": 1,
    "USDC": 1,
    "DAI": 1,
}

whale_addresses = {
    "USDC": "0x0a59649758aa4d66e25f08dd01271e891fe52199",
    "USDT": "0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503",
    "WETH": "0x2f0b23f53734252bda2277357e97e1517d6b042a",
}

# TODO: uncomment those tokens you want to test as want
@pytest.fixture(
    params=[
        "USDC",  # USDC
        "USDT",  # USDT
#        "WETH",  # WETH
    ],
    scope="session",
    autouse=True,
)
def token(request):
    yield Contract(token_addresses[request.param])

@pytest.fixture
def token_lp(token, lp_staker):
    yield Contract(lp_staker.poolInfo(token_id[token.symbol()])["lpToken"])

@pytest.fixture
def stargate_weth():
    yield accounts.at("0x72E2F4830b9E45d52F80aC08CB2bEC0FeF72eD9c", force=True) 

@pytest.fixture(scope="session", autouse=True)
def token_whale(accounts, token):
    yield accounts.at(whale_addresses[token.symbol()], force=True)

@pytest.fixture(autouse=True)
def amount(token, token_whale, user):
    # this will get the number of tokens (around $1m worth of token)
    amillion = round(100_000 / token_prices[token.symbol()])
    amount = amillion * 10 ** token.decimals()
    # # In order to get some funds for the token you are about to use,
    # # it impersonate a whale address
    if amount > token.balanceOf(token_whale):
        amount = token.balanceOf(token_whale)
    token.transfer(user, amount, {"from": token_whale})
    yield amount

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
def usdc():
    token_address = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    yield Contract(token_address)

@pytest.fixture
def stg_token():
    token_address = "0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6"
    yield Contract(token_address)


@pytest.fixture
def stg_whale(accounts):
    #yield accounts.at("0x32e46cab87109ee6ede7d03d263c47be987238b9", force=True)
    yield accounts.at("0x28C6c06298d514Db089934071355E5743bf21d60", force=True)


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
def curve_pool():
    yield Contract("0x3211C6cBeF1429da3D0d58494938299C92Ad5860")


@pytest.fixture
def ymechs_safe():
    yield Contract("0x2C01B4AD51a67E2d8F02208F54dF9aC4c0B778B6")


@pytest.fixture
def stargate_token_pool(token_lp):
    yield token_lp


@pytest.fixture(scope="module")
def sushiswap_router(Contract):
    yield Contract("0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F")


@pytest.fixture(scope="module")
def multicall_swapper(interface):
    yield interface.MultiCallOptimizedSwapper(
        "0xB2F65F254Ab636C96fb785cc9B4485cbeD39CDAA"
    )


@pytest.fixture(scope="session")
def liquidity_pool_id_in_lp_staking(token):
    yield token_id[token.symbol()]


@pytest.fixture
def SGT_whale(accounts):
    yield accounts.at("0x485544e6fbef56d5bff61632b519ba0debdf28c1", force=True)


@pytest.fixture
def token_LP_whale(accounts):
    yield accounts.at("0xf8fd11594574f6aeb3193e779b7b1cf5ef6432f4", force=True)


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
def univ2_router():
    address = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    yield Contract(address)


@pytest.fixture
def ymechs_safe():
    yield Contract("0x2C01B4AD51a67E2d8F02208F54dF9aC4c0B778B6")


@pytest.fixture
def weth():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    yield Contract(token_address)


@pytest.fixture
def price_feed():
    token_address = "0x986b5E1e1755e3C2440e960477f25201B0a8bbD4"
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
    vault.initialize(token, gov, rewards, "", "", guardian, management, {"from": gov})
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault

@pytest.fixture
def strategy(
    strategist,
    keeper,
    vault,
    Strategy,
    gov,
    lp_staker,
    liquidity_pool_id_in_lp_staking,
    weth,
    trade_factory,
    price_feed,
    ymechs_safe,
):
    strategy = strategist.deploy(
        Strategy,
        vault,
        lp_staker,
        liquidity_pool_id_in_lp_staking,
        price_feed,
        "StrategyStargateUSDC",
    )
    strategy.setKeeper(keeper, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    trade_factory.grantRole(
        trade_factory.STRATEGY(),
        strategy.address,
        {"from": ymechs_safe, "gas_price": "0 gwei"},
    )
    strategy.setTradeFactory(trade_factory.address, {"from": gov})

    yield strategy


@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    yield 1e-5
