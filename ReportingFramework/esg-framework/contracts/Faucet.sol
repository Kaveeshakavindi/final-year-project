// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.19;

contract Faucet {
    uint public a;

    constructor() {
        a = 1;
    }

    event ValueChanged(uint oldValue, uint newValue, address indexed caller);
    
    function setA(uint newA) public{
        require(newA != a, "same value");
        uint old = a;
        a = newA;
        emit ValueChanged(old, newA, msg.sender);
    }
}

//truffle compile
//truffle migrate -reset 
//truffle console 

//----TEST IN CONSOLE & RESULTS------------
//1. Deployed the contract (Faucet in your case).
// truffle(ganache)> const t = await Faucet.deployed() 
// undefined 

//2. Read initial state → a was 1:
// truffle(ganache)> (await t.a()).toString() 
// '1' 

//3. Sent a transaction to update state (setA(42)), which mined a block:
// truffle(ganache)> let tx = await t.setA(42) 
// undefined 

//4. Verified the state changed → a is now 42:
// truffle(ganache)> (await t.a()).toString() 
// '42' 

//5. Checked emitted event → ValueChanged:
// truffle(ganache)> tx.logs[0].event 
// 'ValueChanged' 

//6. Inspected event arguments →
// truffle(ganache)> tx.logs[0].args 
// Result { '0': BN { negative: 0, words: [ 1, <1 empty item> ], length: 1, red: null }, '1': BN { negative: 0, words: [ 42, <1 empty item> ], length: 1, red: null }, '2': '0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1', __length__: 3, oldValue: BN { negative: 0, words: [ 1, <1 empty item> ], length: 1, red: null }, newValue: BN { negative: 0, words: [ 42, <1 empty item> ], length: 1, red: null }, caller: '0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1' } truffle(ganache)>
// RESULT SUMMARY :
// oldValue = 1
// newValue = 42
// caller = your account (0x90F8...)

//From this we can decide:
// Your smart contract deployment is working.
// State variables update correctly when transactions are sent.
// Events are being emitted and carry the right data.
// You’re correctly interacting with the contract using Truffle & Ganache.
// It’s basically a full round-trip test:
// 📥 Deploy → 📤 Read → 🔄 Write → 📤 Read again → 📡 Listen to events.
//------------------------------------