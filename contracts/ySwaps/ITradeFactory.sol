// SPDX-License-Identifier: MIT
pragma solidity 0.6.12;

interface ITradeFactory {
    function enable(address _tokenIn, address _tokenOut) external;
}