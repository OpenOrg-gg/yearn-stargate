// SPDX-License-Identifier: AGPL-3.0

pragma solidity 0.6.12;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

interface IDetailedERC20 is IERC20 {
    function decimals() external view returns (uint8);
}
