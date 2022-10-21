import pytest
from brownie import config
from brownie import Contract


token_addresses = {
    "USDC": "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",  # USDC
    "WETH": "0x4200000000000000000000000000000000000006",  # WETH != 0xb69c8CBCD90A39D8D3d3ccf0a3E968511C3856A0
}

token_id = {
    "USDC": 0,  # USDC
    "WETH": 1,  # WETH ! = 
}

token_prices = {
    "WBTC": 35_000,
    "WETH": 2_000,
    "USDT": 1,
    "USDC": 1,
    "DAI": 1,
}

token_isWeth = {
    "USDC": False,  # USDC
    "WETH": True,  # WETH 
}

whale_addresses = {
    "USDC": "0xd6216fc19db775df9774a6e33526131da7d19a2c",
    "WETH": "0xBA12222222228d8Ba445958a75a0704d566BF2C8",
}

# TODO: uncomment those tokens you want to test as want
@pytest.fixture(
    params=[
        "USDC",  # USDC
        "WETH",  # WETH
    ],
    scope="session",
    autouse=True,
)
def token(request):
    yield Contract(token_addresses[request.param])

#Optimism has OP rewards, not STG rewards:
@pytest.fixture
def emissionTokenIsSTG():
    yield False

@pytest.fixture
def token_lp(token, lp_staker):
    yield Contract(lp_staker.poolInfo(token_id[token.symbol()])["lpToken"])

@pytest.fixture
def wantIsWeth(token):
    yield token_isWeth[token.symbol()]

@pytest.fixture
def stargate_weth():
    yield accounts.at("0xb69c8CBCD90A39D8D3d3ccf0a3E968511C3856A0", force=True) 

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
    yield accounts.at("0xF5d9D6133b698cE29567a90Ab35CfB874204B3A7", force=True)

@pytest.fixture
def oChad(accounts):
    yield accounts.at("0xF5d9D6133b698cE29567a90Ab35CfB874204B3A7", force=True)

@pytest.fixture
def user(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts, gov):
    yield gov


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
    token_address = "0x7F5c764cBc14f9669B88837ca1490cCa17c31607"
    yield Contract(token_address)


@pytest.fixture
def stg_token():
    token_address = "0x296F55F8Fb28E498B858d0BcDA06D955B2Cb3f97"
    yield Contract(token_address)


@pytest.fixture
def stg_whale(accounts):
    #yield accounts.at("0x32e46cab87109ee6ede7d03d263c47be987238b9", force=True)
    yield accounts.at("0x3869dbae46454efb20e20c136e751a272922530d", force=True)


@pytest.fixture
def op_whale(accounts):
    yield accounts.at("0x790b4086d106eafd913e71843aed987efe291c92", force=True)

@pytest.fixture
def lp_staker():
    address = "0x4DeA9e918c6289a52cd469cAC652727B7b412Cd2"
    yield Contract(address)


@pytest.fixture
def stargate_router():
    address = "0xB0D502E938ed5f4df2E681fE6E419ff29631d62b"
    yield Contract(address)


@pytest.fixture
def trade_factory():
    yield Contract("0x21d7B09Bcf08F7b6b872BED56cB32416AE70bCC8")

@pytest.fixture
def trade_factory_gov(accounts,trade_factory):
    yield accounts.at(trade_factory.governance(), force=True)

@pytest.fixture
def ymechs_safe(accounts, trade_factory, trade_factory_gov):
    trade_factory.addMech(accounts[7], {"from": trade_factory_gov})
    #trade_factory.grantRole(trade_factory.STRATEGY(), strategy.address, {"from": ymechs_safe, "gas_price": "0 gwei"},)
    yield accounts[7]

@pytest.fixture
def curve_pool():
    yield Contract("0x3211C6cBeF1429da3D0d58494938299C92Ad5860")


#@pytest.fixture
#def ymechs_safe():
#    yield Contract("0x21d7B09Bcf08F7b6b872BED56cB32416AE70bCC8")


@pytest.fixture
def stargate_token_pool(token_lp):
    yield token_lp


@pytest.fixture(scope="module")
def sushiswap_router(Contract):
    yield router

@pytest.fixture
def velodrome_router(): #velodrome
    yield Contract('0xa132DAB612dB5cB9fC9Ac426A0Cc215A3423F9c9')

@pytest.fixture
def op_token():
    yield Contract('0x4200000000000000000000000000000000000042')

#@pytest.fixture(scope="module")
#def multicall_swapper(interface):
#    yield interface.MultiCallOptimizedSwapper("0xB2F65F254Ab636C96fb785cc9B4485cbeD39CDAA")

@pytest.fixture(scope="module")
def multicall_swapper(interface):
    yield interface.MultiCallOptimizedSwapper("0xcA11bde05977b3631167028862bE2a173976CA11")

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
def univ3_swapper():
    address = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    yield Contract(address)


@pytest.fixture
def weth():
    token_address = "0x4200000000000000000000000000000000000006"
    yield Contract(token_address)

@pytest.fixture
def rando(accounts):
    yield accounts[9]

@pytest.fixture
def price_feed():
    #token_address = "0x986b5E1e1755e3C2440e960477f25201B0a8bbD4"
    #dummy address:
    token_address = "0x4200000000000000000000000000000000000006"
    yield Contract(token_address)

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
    token,
    keeper,
    vault,
    Strategy,
    gov,
    lp_staker,
    liquidity_pool_id_in_lp_staking,
    weth,
    trade_factory,
    #price_feed,
    wantIsWeth,
    emissionTokenIsSTG,
    BaseFeeDummy,
    oChad,
):
    strategy = strategist.deploy(
        Strategy,
        vault,
        lp_staker,
        liquidity_pool_id_in_lp_staking,
        wantIsWeth,
        emissionTokenIsSTG,
        #price_feed,
        f"StrategyStargate{token.symbol()}",
    )
    strategy.setKeeper(keeper, {"from": gov})
    strategy.setDoHealthCheck(False, {"from": gov})
    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    strategy.setTradeFactory(trade_factory.address, {"from": gov})
    baseFeeDummy = BaseFeeDummy.deploy(oChad, {"from": strategist})
    strategy.setBaseFeeOracle(baseFeeDummy, {"from": gov})

    yield strategy


@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    yield 1e-5
