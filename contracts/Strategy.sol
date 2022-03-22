// SPDX-License-Identifier: AGPL-3.0
// Feel free to change the license, but this is what we use

// Feel free to change this version of Solidity. We support >=0.6.0 <0.7.0;
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

// These are the core Yearn libraries
import {
    BaseStrategy,
    StrategyParams
} from "@yearnvaults/contracts/BaseStrategy.sol";
import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

// Import interfaces for many popular DeFi projects, or add your own!
//import "../interfaces/<protocol>/<Interface>.sol";

interface IStargateFarm{
    function pendingStargate(uint256, address) external view returns(uint256);
    function userInfo(uint256, address) external view returns(uint256,uint256);
    function deposit(uint256,uint256) external;
    function withdraw(uint256,uint256) external;
    function emergencyWithdraw(uint256) external;
}

interface IStargateRouter{
    function addLiquidity(uint256,uint256,address) external;
    function instantRedeemLocal(uint16 _srcPoolId, uint256 _amountLP, address _to) external;
}

interface ISTGToken is IERC20 {
    function amountLPtoLD(uint256 _amount) external view returns (uint256);
}


interface IUniV3 {
    struct ExactInputParams {
        bytes path;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
    }

    function exactInput(ExactInputParams calldata params)
        external
        payable
        returns (uint256 amountOut);
}

contract Strategy is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    //max for 256-1 on approve
    uint256 public constant max = type(uint256).max;

    //$USDC Token
    IERC20 public constant USDC = IERC20(0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48);

    IERC20 internal constant weth =
        IERC20(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);
    
    address internal constant uniswapv3 =
        0xE592427A0AEce92De3Edee1F18E0157C05861564;

    //$STG Token
    ISTGToken public constant STG = ISTGToken(0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6);

    //Staking Contract
    IStargateFarm public constant StakingContract = IStargateFarm(0xB0D502E938ed5f4df2E681fE6E419ff29631d62b);

    //Router
    IStargateRouter public StarGateRouter = IStargateRouter(0x8731d54E9D02c286767d56ac03e8037C07e01e98);

    //Pool Token
    ISTGToken public constant pUSDC = ISTGToken(0xdf0770dF86a8034b3EFEf0A1Bb3c889B8332FF56);

    //PoolID for Router:
    uint16 public constant PoolID = 1;

    //PID for Farming
    uint16 public constant PID = 0;

    constructor(address _vault) public BaseStrategy(_vault) {
        // You can set these parameters on deployment to whatever you want
        // maxReportDelay = 6300;
        // profitFactor = 100;
        // debtThreshold = 0;
        USDC.approve(0x8731d54E9D02c286767d56ac03e8037C07e01e98,max);
        STG.approve(uniswapv3, max);
        weth.approve(uniswapv3, max);
        pUSDC.approve(0xB0D502E938ed5f4df2E681fE6E419ff29631d62b,max);

    }

    // ******** OVERRIDE THESE METHODS FROM BASE CONTRACT ************

    function name() external view override returns (string memory) {
        // Add your own name here, suggestion e.g. "StrategyCreamYFI"
        return "StrategyStargateUSDConEthereum";
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        // TODO: Build a more accurate estimate using the value of all positions in terms of `want`
        (uint256 bal,) = StakingContract.userInfo(PID,address(this));
        uint256 converted = pUSDC.amountLPtoLD(bal);
        return want.balanceOf(address(this)).add(converted);
    }

    function balanceOfWant() public view returns (uint256){
        return want.balanceOf(address(this));
    }

    function balanceOfReward() public view returns (uint256){
        return STG.balanceOf(address(this));
    }

    function pendingRewards() public view returns(uint256){
        uint256 pending = StakingContract.pendingStargate(PID,address(this));
        return pending;
    }

    function _addToLP(uint256 _amount) internal {
        StarGateRouter.addLiquidity(PoolID, _amount, address(this));
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        //grab the estimate total debt from the vault
        uint256 vaultDebt = vault.strategies(address(this)).totalDebt;

        //Perform a 0 deposit to claim any outstanding rewards
        StakingContract.deposit(0,0);

        //check STG
        uint256 looseReward = STG.balanceOf(address(this));
        if(looseReward != 0){
            uint256 wethOutput = _sellSTGForWETH(looseReward);
            _sellWETHforUSDC(wethOutput);
        }

        uint256 finalProfit = estimatedTotalAssets().sub(vaultDebt);

        if(finalProfit < _debtOutstanding){
            _profit = 0;
            _debtPayment = balanceOfWant();
            _loss = _debtOutstanding.sub(_debtPayment);
        } else {
            _profit = finalProfit.sub(_debtOutstanding);
            _debtPayment = _debtOutstanding;
        }


        // TODO: Do stuff here to free up any returns back into `want`
        // NOTE: Return `_profit` which is value generated by all positions, priced in `want`
        // NOTE: Should try to free up at least `_debtOutstanding` of underlying position
    }

        // Sells our STG for WETH
    function _sellSTGForWETH(uint256 _amount) internal returns (uint256) {
        uint256 _wethOutput =
            IUniV3(uniswapv3).exactInput(
                IUniV3.ExactInputParams(
                    abi.encodePacked(
                        address(STG),
                        uint24(500),
                        address(weth)
                    ),
                    address(this),
                    block.timestamp,
                    _amount,
                    uint256(1)
                )
            );
        return _wethOutput;
    }

            // Sells our WETH for USDC
    function _sellWETHforUSDC(uint256 _amount) internal returns (uint256) {
        uint256 _usdcOutput =
            IUniV3(uniswapv3).exactInput(
                IUniV3.ExactInputParams(
                    abi.encodePacked(
                        address(weth),
                        uint24(500),
                        address(USDC)
                    ),
                    address(this),
                    block.timestamp,
                    _amount,
                    uint256(1)
                )
            );
        return _usdcOutput;
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        // TODO: Do something to invest excess `want` tokens (from the Vault) into your positions
        // NOTE: Try to adjust positions so that `_debtOutstanding` can be freed up on *next* harvest (not immediately)

        uint256 looseWant = balanceOfWant();
        if(looseWant > 10000e18){
            _addToLP(looseWant);
        }
    }

    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        // TODO: Do stuff here to free up to `_amountNeeded` from all positions back into `want`
        // NOTE: Maintain invariant `want.balanceOf(this) >= _liquidatedAmount`
        // NOTE: Maintain invariant `_liquidatedAmount + _loss <= _amountNeeded`
        (uint256 bal,) = StakingContract.userInfo(PID,address(this));
        uint256 converted = pUSDC.amountLPtoLD(bal);
        uint256 totalAssets = want.balanceOf(address(this));

        if(totalAssets < _amountNeeded && converted.add(totalAssets) > _amountNeeded){
            //withdraw from farm
            StakingContract.withdraw(PID,bal);

            //withdraw from pool
            StarGateRouter.instantRedeemLocal(PoolID, bal, address(this));

            //Check current usdc balance

            uint256 postWithdrawUSDC = USDC.balanceOf(address(this));

            //redeposit to pool
            if(postWithdrawUSDC > _amountNeeded){
                StarGateRouter.addLiquidity(PoolID, postWithdrawUSDC.sub(_amountNeeded), address(this));
            
                //redeposit to farm
                StakingContract.deposit(PID,pUSDC.balanceOf(address(this)));
            }
        }

        //recheck total assets
        totalAssets = want.balanceOf(address(this));

        if (_amountNeeded > totalAssets) {
            _liquidatedAmount = totalAssets;
            _loss = _amountNeeded.sub(totalAssets);
        } else {
            _liquidatedAmount = _amountNeeded;
        }
    }

    function liquidateAllPositions() internal override returns (uint256) {
        // TODO: Liquidate all positions and return the amount freed.
        StakingContract.emergencyWithdraw(PID);
        if(pUSDC.balanceOf(address(this)) > 0){
            StarGateRouter.instantRedeemLocal(PoolID, pUSDC.balanceOf(address(this)), address(this));
        }
        return want.balanceOf(address(this));
    }

    // NOTE: Can override `tendTrigger` and `harvestTrigger` if necessary

    function prepareMigration(address _newStrategy) internal override {
        // TODO: Transfer any non-`want` tokens to the new strategy
        // NOTE: `migrate` will automatically forward all `want` in this strategy to the new one
    }

    // Override this to add all tokens/tokenized positions this contract manages
    // on a *persistent* basis (e.g. not just for swapping back to want ephemerally)
    // NOTE: Do *not* include `want`, already included in `sweep` below
    //
    // Example:
    //
    //    function protectedTokens() internal override view returns (address[] memory) {
    //      address[] memory protected = new address[](3);
    //      protected[0] = tokenA;
    //      protected[1] = tokenB;
    //      protected[2] = tokenC;
    //      return protected;
    //    }
    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {}

    /**
     * @notice
     *  Provide an accurate conversion from `_amtInWei` (denominated in wei)
     *  to `want` (using the native decimal characteristics of `want`).
     * @dev
     *  Care must be taken when working with decimals to assure that the conversion
     *  is compatible. As an example:
     *
     *      given 1e17 wei (0.1 ETH) as input, and want is USDC (6 decimals),
     *      with USDC/ETH = 1800, this should give back 1800000000 (180 USDC)
     *
     * @param _amtInWei The amount (in wei/1e-18 ETH) to convert to `want`
     * @return The amount in `want` of `_amtInEth` converted to `want`
     **/
    function ethToWant(uint256 _amtInWei)
        public
        view
        virtual
        override
        returns (uint256)
    {
        // TODO create an accurate price oracle
        return _amtInWei;
    }
}
