// SPDX-License-Identifier: AGPL-3.0

pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

// These are the core Yearn libraries
import {
    BaseStrategy,
    StrategyParams
} from "@yearnvaults/contracts/BaseStrategy.sol";
import "@openzeppelin/contracts/math/Math.sol";
import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

import "../interfaces/Stargate/IStargateRouter.sol";
import "../interfaces/Stargate/IPool.sol";
import "../interfaces/Stargate/ILPStaking.sol";
import "../interfaces/Uniswap/IUniV3.sol"; // TODO: replace with ySwaps

contract Strategy is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    IERC20 internal constant weth =
        IERC20(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);

    uint constant private max = type(uint).max;
    bool internal isOriginal = true;

    uint24 public poolFee;

    IUniV3 public uniV3Swapper;

    uint256 public liquidityPoolID;
    uint256 public liquidityPoolIDInLPStaking; // Each pool has a main Pool ID and then a separate Pool ID that refers to the pool in the LPStaking contract.

    IERC20 public STG;
    IPool public liquidityPool;
    IERC20 public lpToken;
    IStargateRouter public stargateRouter;
    ILPStaking public lpStaker;

    string internal strategyName;

 constructor(
        address _vault,
        address _lpStaker,
        uint16 _liquidityPoolIDInLPStaking,
        address _uniV3Swapper,
        string memory _strategyName
    ) public BaseStrategy(_vault) {
        _initializeThis(
            _lpStaker,
            _liquidityPoolIDInLPStaking,
            _uniV3Swapper,
            _strategyName
        );
    }

      function initialize(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _lpStaker,
        uint16 _liquidityPoolIDInLPStaking,
        address _uniV3Swapper,
        string memory _strategyName
    ) public {
        // Make sure we only initialize one time
        require(address(lpStaker) == address(0)); // dev: strategy already initialized

        address sender = msg.sender;

        // Initialize BaseStrategy
        _initialize(_vault, _strategist, _rewards, _keeper);

        // Initialize cloned instance
        _initializeThis(
            _lpStaker,
            _liquidityPoolIDInLPStaking,
            _uniV3Swapper,
            _strategyName
        );
    }

     function _initializeThis(
            address _lpStaker,
            uint16 _liquidityPoolIDInLPStaking,
            address _uniV3Swapper,
            string memory _strategyName
    ) internal {
        lpStaker = ILPStaking(_lpStaker);
        STG = IERC20(lpStaker.stargate());
        liquidityPoolIDInLPStaking = _liquidityPoolIDInLPStaking;

        lpToken = lpStaker.poolInfo(_liquidityPoolIDInLPStaking).lpToken;

        liquidityPool = IPool(address(lpToken));
        liquidityPoolID = liquidityPool.poolId();
        stargateRouter = IStargateRouter(liquidityPool.router());

        want.safeApprove(address(stargateRouter), max);
        lpToken.safeApprove(address(lpStaker), max);

        require(address(want) == liquidityPool.token());

        poolFee = 3000;// We set the pool fee to 0.3%.

        strategyName = _strategyName;
        uniV3Swapper = IUniV3(_uniV3Swapper);
    }
event Cloned(address indexed clone);
    function clone(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _lpStaker,
        uint16 _liquidityPoolIDInLPStaking,
        address _uniV3Swapper,
        string memory _strategyName
    ) external returns (address payable newStrategy) {
        require(isOriginal);

        bytes20 addressBytes = bytes20(address(this));

        assembly {
        // EIP-1167 bytecode
            let clone_code := mload(0x40)
            mstore(clone_code, 0x3d602d80600a3d3981f3363d3d373d3d3d363d73000000000000000000000000)
            mstore(add(clone_code, 0x14), addressBytes)
            mstore(add(clone_code, 0x28), 0x5af43d82803e903d91602b57fd5bf30000000000000000000000000000000000)
            newStrategy := create(0, clone_code, 0x37)
        }

        Strategy(newStrategy).initialize(_vault, _strategist, _rewards, _keeper, _lpStaker, _liquidityPoolIDInLPStaking, _uniV3Swapper, _strategyName);

        emit Cloned(newStrategy);
    }

    function name() external view override returns (string memory) {
        return strategyName; // E.g., 'StrategyStargateUSDC'
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        return balanceOfWant().add(valueOfLPTokens());
    }

    function pendingSTGRewards() public view returns (uint256) {
        return
            lpStaker.pendingStargate(liquidityPoolIDInLPStaking, address(this));
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
        if (pendingSTGRewards() > 0) {
            lpStaker.deposit(liquidityPoolIDInLPStaking, 0);
        }

        //check STG
        uint256 _looseSTG = balanceOfSTG();
        if (_looseSTG != 0) {
            _sellRewards();
        }

        //grab the estimate total debt from the vault
        uint256 _vaultDebt = vault.strategies(address(this)).totalDebt;
        uint256 _totalAssets = estimatedTotalAssets();

        if (_totalAssets >= _vaultDebt) {
            // Implicitly, _profit & _loss are 0 before we change them.
            _profit = _totalAssets.sub(_vaultDebt);
        } else {
            _loss = _vaultDebt.sub(_totalAssets);
        }

        //free up _debtOutstanding + our profit, and make any necessary adjustments to the accounting.

        (uint256 _amountFreed, uint256 _liquidationLoss) =
            liquidatePosition(_debtOutstanding.add(_profit));

        _loss = _loss.add(_liquidationLoss);

        _debtPayment = Math.min(_debtOutstanding, _amountFreed);

        if (_loss > _profit) {
            _loss = _loss.sub(_profit);
            _profit = 0;
        } else {
            _profit = _profit.sub(_loss);
            _loss = 0;
        }
    }

    event sellingRewards(address swapper, uint256 amountIn, uint24 fee);
    function _sellRewards() internal {
        uint256 availableSTG = balanceOfSTG();
        _checkAllowance(address(uniV3Swapper), address(STG), availableSTG);

        IUniV3.ExactInputParams memory params =
            IUniV3.ExactInputParams({
                path: abi.encodePacked(address(STG), poolFee, address(want)),
                recipient: address(this),
                deadline: block.timestamp,
                amountIn: availableSTG,
                amountOutMinimum: 0
            });
        emit sellingRewards(address(uniV3Swapper), availableSTG, poolFee);
        uniV3Swapper.exactInput(params);
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        uint256 _looseWant = balanceOfWant();

        if (_looseWant > _debtOutstanding) {
            uint256 _amountToDeposit = _looseWant.sub(_debtOutstanding);

            if(_amountToDeposit > 0){
                _addToLP(_amountToDeposit);
            }
            if(balanceOfUnstakedLPToken() > 0){
                lpStaker.deposit(
                    liquidityPoolIDInLPStaking,
                    balanceOfUnstakedLPToken()
                );
            }
        }
    }

    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        uint256 _liquidAssets = balanceOfWant();

        if (_liquidAssets < _amountNeeded) {
            // TODO: maybe instead of withdrawing whole balance from lpStaker & re-depositing, withdraw only the amount we need
            lpStaker.withdraw(
                liquidityPoolIDInLPStaking,
                balanceOfStakedLPToken()
            );

            if(balanceOfUnstakedLPToken() > 0){
                //withdraw from pool
                _withdrawFromLP(balanceOfUnstakedLPToken());
            }

            //check current want balance
            uint256 _postWithdrawWant = balanceOfWant();

            //redeposit to pool
            if (_postWithdrawWant > _amountNeeded) {
                _addToLP(_postWithdrawWant.sub(_amountNeeded));

                if(balanceOfUnstakedLPToken() > 0){
                    //redeposit to farm
                    lpStaker.deposit(
                        liquidityPoolIDInLPStaking,
                        balanceOfUnstakedLPToken()
                    );
                }
            }

            _liquidAssets = balanceOfWant();
        }

        if (_amountNeeded > _liquidAssets) {
            _liquidatedAmount = _liquidAssets;
            _loss = _amountNeeded.sub(_liquidAssets);
        } else {
            _liquidatedAmount = _amountNeeded;
        }
    }

    function liquidateAllPositions() internal override returns (uint256) {
        lpStaker.emergencyWithdraw(liquidityPoolIDInLPStaking);

        uint256 _lpTokenBalance = balanceOfUnstakedLPToken();
        if (_lpTokenBalance > 0) {
            _withdrawFromLP(_lpTokenBalance);
        }
        return balanceOfWant();
    }

    // NOTE: Can override `tendTrigger` and `harvestTrigger` if necessary

    function prepareMigration(address _newStrategy) internal override {
        // TODO: Transfer any non-`want` tokens to the new strategy
        // NOTE: `migrate` will automatically forward all `want` in this strategy to the new one
         lpStaker.emergencyWithdraw(liquidityPoolIDInLPStaking);
         lpToken.safeTransfer(_newStrategy,lpToken.balanceOf(address(this)));
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

    // --------- UTILITY & HELPER FUNCTIONS ------------

    function _addToLP(uint256 _amount) internal {
        // Nice! DRY principle
        _amount = Math.min(balanceOfWant(), _amount); // we don't want to add to LP more than we have
        _checkAllowance(address(stargateRouter), address(want), _amount);
        stargateRouter.addLiquidity(liquidityPoolID, _amount, address(this));
    }

    function _withdrawFromLP(uint256 _lpAmount) internal {
        _lpAmount = Math.min(balanceOfUnstakedLPToken(), _lpAmount); // we don't want to withdraw more than we have
        stargateRouter.instantRedeemLocal(
            uint16(liquidityPoolID),
            _lpAmount,
            address(this)
        );
    }

    function balanceOfWant() public view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function valueOfLPTokens() public view returns (uint256) {
        uint256 _totalLPTokenBalance = balanceOfAllLPToken();

        return liquidityPool.amountLPtoLD(_totalLPTokenBalance);
    }

    function balanceOfAllLPToken() public view returns (uint256) {
        return balanceOfUnstakedLPToken().add(balanceOfStakedLPToken());
    }

    function balanceOfUnstakedLPToken() public view returns (uint256) {
        return lpToken.balanceOf(address(this));
    }

    function balanceOfStakedLPToken() public view returns (uint256) {
        return
            lpStaker.userInfo(liquidityPoolIDInLPStaking, address(this)).amount;
    }

    function balanceOfSTG() public view returns (uint256) {
        return STG.balanceOf(address(this));
    }

    // _checkAllowance adapted from https://github.com/therealmonoloco/liquity-stability-pool-strategy/blob/1fb0b00d24e0f5621f1e57def98c26900d551089/contracts/Strategy.sol#L316

    function _checkAllowance(
        address _contract,
        address _token,
        uint256 _amount
    ) internal {
        if (IERC20(_token).allowance(address(this), _contract) < _amount) {
            IERC20(_token).safeApprove(_contract, 0);
            IERC20(_token).safeApprove(_contract, _amount);
        }
    }

    function setPoolFee(uint24 _poolFee) external onlyVaultManagers {
        poolFee = _poolFee;
    }
}
