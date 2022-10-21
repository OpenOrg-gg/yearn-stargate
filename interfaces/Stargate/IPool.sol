// SPDX-License-Identifier: BUSL-1.1

pragma solidity 0.6.12;

interface IPool {
    function poolId() external view returns (uint256); // shared id between chains to represent same pool
    function token() external view returns (address); // the token for the pool
    function router() external view returns (address); // the router for the pool
    function totalLiquidity() external view returns (uint256); // the total amount of tokens added on this side of the chain (fees + deposits - withdrawals)
    function totalSupply() external view returns (uint256);
    function convertRate() external view returns (uint256); // the decimals for the token

    function amountLPtoLD(uint256 _amountLP) external view returns (uint256);


}
