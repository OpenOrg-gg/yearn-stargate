># Protocol Due Diligence: Stargate (STG)
[ToC]

## Stargate Overview
- [Stargate](https://stargate.finance/)
- [Gov](https://commonwealth.im/stargate-finance/)
- [Docs](https://stargateprotocol.gitbook.io/stargate/)
- [Audit](https://github.com/Zellic/publications/blob/master/LayerZero%20Audit%20Report.pdf) -- only one audit so far, by new auditing entity.

General overview of product: https://stargateprotocol.gitbook.io/stargate/v/user-docs/

How Rewards Work:
https://stargateprotocol.gitbook.io/stargate/v/user-docs/tokenomics/allocations-and-lockups

How fee collection works:
https://stargateprotocol.gitbook.io/stargate/v/user-docs/stargate-features/pool

## Rug-ability
**Multi-sig:** Yes
    - Current Router and Farm owner is by a multisig - 0x65bb797c2b9830d891d87288f029ed8dacc19705
    - Owner can use `setBridgeAndFactory()` on `Router` to change the current bridging system, and factory. Should not affect LP positions or rewards, but would need migration.
    - Owner cannot withdraw or manage user funds in `Router` or `Pool` or in MasterChef fork for farming.
    - Owner cannot block the use of `instantRedeemLocal()` for withdrawing underlying USDC from `Pool`.
    - Owner cannot block the use of `emergencyWithdraw()` on MasterChef fork for withdrawing LP tokens from staking.
    - There is no withdraw fee or deduction that can be used to hold assets hostage.
    - Owner has no manner to directly mint pool tokens to dilute the pool.
    - Owner can use `updateRewardPerblockAndEndBlock()` to change reward pace.
    - Checked that `emergencyWithdraw()` is not blocked by any action admin can use.
    - Rewards are managed by MasterFarmer contract. Rewards not claimed frequently can be reduced if rewards rate is changed between checkins.
    
The 3 multisigs for mainnet are the Lz/Stargate Founders:

Ryan Zarick ( @ryanzarick )
Bryan Pellegrino ( @PrimordialAA )
Caleb Banister ( @cb_LayerZero )

On non ETH chains they also added team members:
Ari Litan (COO)
Shahrair Hafizi (GC)
    
**Conclusion:** There is a multisig in place and safe guards to prevent any abuse risk by multisig.

**Upgradable Contracts:** No
- All contracts for the rewards seem static and would require a migration action from the user.

**Decentralization:**
- There is no active governor contract.

## Audit Reports
Single audit performed by new entity Zellic.

https://github.com/Zellic/publications/blob/master/LayerZero%20Audit%20Report.pdf

High risk issues were resolved; but it should be noted that the contracts are complex, extensive and use a lot of non-standard functionality, such as Stargate using its own safeStargateTransfer for transfering tokens.

## Strategy Details
### Summary
The `Stargate` strategy deposits users `want` (USDC or USDT) into pools through the `Stargate Router` at `0x8731d54E9D02c286767d56ac03e8037C07e01e98`.

It then stakes those tokens on the `LPStaking` contract (a customized MasterChef fork) located at `0xB0D502E938ed5f4df2E681fE6E419ff29631d62b`.

The Stargate system essentially acts as a cross-chain AMM, like a bridged version of Curve.

This contract earns:
 - Exchange fees when users transfer assets between chains.
 - $STG emissions from farming.

The strategy will sell farmed $STG and put it back into want.

### Strategy current APR
Currently the strategy yields 20%-30% (not accounting for compounding) depending on the asset and chain.

It is expected this will decline with upcoming farming epochs, but may be offset by fees.

It is currently earning these yields despite a total TVL of >$1.6B in stablecoins.

#### Stargate Transfer Fees
Every transaction that swaps using the bridge, either between chains, or between assets results in a .06% fee, of which 0.045% of that fee accumulated goes to LPs.

It is accumulated in the LP token directly.

#### STG Emissions
Similar to standard farming, Stargate staking also gives STG emissions.

The emissions equate to 2.11% of the current STG allocation (https://stargateprotocol.gitbook.io/stargate/v/user-docs/tokenomics/allocations-and-lockups) and is slated to last until 2025.

It is expected that some portion of the community allocation will be used to increase emissions, but it is not yet confirmed.

### Vault/Strategy Pitfalls
Here are a couple of things which are out of the ordinary and might be of a surprise when reading the code.

#### Pool IDs
Each asset has two Pool IDs, one declared in the `Router` that is the Pool ID for adding liquidity to the bridges.

The other is in the `LPStaking` contract, where we deposit LP tokens to farm.

These Pool IDs represented in our code by `PID` and `PoolID` are not the same number.

#### Recently Launched LP Token has 1:1.
Since Stargate has recently launched and not accumulated much from transaction fees, at the time of development the ratio of USDC to s*USDC is 1:1. As an LP token this will shift overtime.


#### There is no withdraw command for LP tokens.
Stargate has users use their own `instantRedeemLocal()` to settle an LP balance into the underlying `want` on the current chain.

#### There is no claim for rewards in farming.
There is no specific `claim` command for rewards from the farming contract. Reward claims happen on deposits and withdraws, and so our contract uses `deposit(0,0)` in lieu of a claim.

#### LP Tokens are not standard ERC20s.
They have their own implementation as `LPTokenERC20.sol` that may behave in non-standard ways.

For example casting as IERC20 and attempting `safeTransferFrom()` failed testing while `safeTransfer()` did not.

#### Uniqe MasterChef Implementation.
Stargate uses a unique MasterChef implementation.

Including their own way of interacting with LP tokens as `safeStargateTransfer(msg.sender, pending);` in the event of an error with the Stargate/LayerZero system this mechanic could break.

The `emergencyWithdraw()` function does fall back to the standard `ERC20.safeTransfer()` method in the event of an issue.

## Path-to-Prod
#### Does Strategy delegate assets?
No

#### Target Prod Vault
- USDC on Ethereum
- USDT on Ethereum
- USDC on Fantom
- USDC on Arbitrum
- USDT on Arbitrum

#### BaseStrategy Version
0.4.3

#### Target Prod Vault Version
0.4.3

### Testing Plan
Strategy currently passes basic tests.

First time strategist could use support from an experienced strategist coming up with a more extensive testing plan.

Current goal is to implement on ApeTax and monitor from there.

#### Ape.tax
##### Will Ape.tax be used?
Yes

##### Will Ape.tax vault be same version # as prod vault?
Yes

##### What conditions are needed to graduate? (e.g. number of harvest cycles, min funds, etc)
 - Be profitable
 - See atleast 5 profitable reward period returns without issue.
 - Ensure slippage is a non-issue with converting funds of at least $100k.

#### Prod Deployment Plan
##### Suggested position in withdrawQueue?
?

##### Does strategy have any deposit/withdraw fees?
No.

##### Suggested debtRatio?
?

#### Checklist
- [ ] Get additional support from experienced strategist on testing
    - [ ] Run extended tests 
- [ ] Deploy vault version to Ape.tax
- [ ] Deploy strategy to mainnet vault
    - [ ] Add strategy
- [ ] Endorse to prod
- [ ] Expand to other networks.
