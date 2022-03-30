from brownie import Strategy, accounts, config, network, project, web3


def main():
    with open('./build/contracts/StrategyFlat.sol', 'w') as f:
        Strategy.get_verification_info()
        f.write(Strategy._flattener.flattened_source)
