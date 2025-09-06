// SPDX-License-Identifier: MIT
//solidity is Ethereum-compatible blockchains
//Remix ide - https://remix.ethereum.org/#lang=en&optimize=false&runs=200&evmVersion=null&version=soljson-v0.8.30+commit.73712a01.js
pragma solidity ^0.8.0;

contract SimpleStorage {
    uint256 private storedNumber;  // state variable

    // Event to log changes
    event NumberUpdated(uint256 oldNumber, uint256 newNumber);

    // Function to set a number
    function setNumber(uint256 _num) public {
        uint256 old = storedNumber;
        
        storedNumber = _num;
        emit NumberUpdated(old, _num);
    }

    // Function to get the current number
    function getNumber() public view returns (uint256) {
        return storedNumber;
    }
}
