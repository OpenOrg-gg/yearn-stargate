// SPDX-License-Identifier: MIT
pragma solidity 0.6.12;

interface ICurve {
    function add_liquidity(uint256[2] calldata amounts, uint256 min_mint_amount)
        external
        payable
        returns (uint256);

    function exchange_underlying(
        int128 i,
        int128 j,
        uint256 dx,
        uint256 min_dy
    ) external returns (uint256);

    function coins(uint256 i) external returns (address);

    function remove_liquidity_one_coin(
        uint256 _token_amount,
        int128 i,
        uint256 _min_amount
    ) external returns (uint256);

    function exchange(
        int128 i,
        int128 j,
        uint256 dx,
        uint256 min_dy
    ) external returns (uint256);

    function get_dy(
        int128 i,
        int128 j,
        uint256 dx
    ) external returns (uint256);
}
