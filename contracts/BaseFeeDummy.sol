// SPDX-License-Identifier: AGPL-3.0

pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

interface IBaseFee {
    function isCurrentBaseFeeAcceptable() external view returns (bool);
}

contract BaseFeeDummy {

    address public baseFeeOracle;
    address public governance;

    constructor(address _governance) public {
        governance = _governance;
    }

    function isCurrentBaseFeeAcceptable() external view returns (bool) {
        if (baseFeeOracle == address(0)){
            return true;
        } else {
            return IBaseFee(baseFeeOracle).isCurrentBaseFeeAcceptable();          
        }
    }

    function setBaseFeeOracle(address _newBaseFeeOracle) public {
        require(msg.sender == governance, "!gov");
        baseFeeOracle = _newBaseFeeOracle;
    }

    function setGovernance(address _newGovernance) public {
        require(msg.sender == governance, "!gov");
        governance = _newGovernance;
    }
    
}
