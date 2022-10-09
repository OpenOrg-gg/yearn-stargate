// SPDX-License-Identifier: AGPL-3.0

pragma solidity 0.6.12;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";

interface IERC20Metadata is IERC20 {
    function symbol() external view returns (string memory);
    function decimals() external view returns (uint8);
    function token() external view returns (address);
}
