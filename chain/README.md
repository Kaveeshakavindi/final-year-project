## Step 1
## Create next app

```bash
npx create-next-app@latest esg-framework
```

## Step 2
## Install ganache

go to https://archive.trufflesuite.com/ganache/ and download.

## Step 3 
## Install truffle

(in next app directory)
```bash
npm install truffle --force -g
npm truffle init
truffle console
```

After installing truffle, go to ganache. Select quickstart. go to settings (right top corner). Click 'Add Project'. go to next app and select truffle-config.js and open. Then restart ganache.

I am using --network ganache according to my truffle-config.js > module.exports > networks > ganache 

```bash
truffle console 
compile
migrate -reset
```

As truffle is a development framework for smart contracts (compile, migrate, test, manage), it does not include its own blockchain node. It expects you to connect to a blockchain network (local, testnet or mainnet). That's when we need Ganache which is a personal Ethereum Blockchain runtime that runs locally. It simulates a real Ethereum network.

When we run ```bash truffle migrate```, truffle looks for a blockchain at the configured address.

Later on you can switch from Ganache to a public testnet (eg: Goerli, Sepolia) or even Ethereum mainnet.

## Interacting with the contract
as we write ```bash await f.setA(23)`` is a state changing function call. When you change storage in Ethereum (e.g., update a variable), you must send a transaction. Transactions cost gas and get recorded on the blockchain. Ganache mines it instantly, so you don’t wait for real miners. This is a transaction.

# Step 4
## Download VSCode extentions

1. Solidity - https://marketplace.visualstudio.com/items?itemName=JuanBlanco.solidity
2. Tailwind CSS - https://marketplace.visualstudio.com/items?itemName=bradlc.vscode-tailwindcss

# Step 5
## Frontend setup
Install web3 to listen to events as they happen and make UI react instantly.

```bash
npm install web3

#typeSript specifit web3 types
npm install --save-dev @types/web3

#to use type BN
npm install bn.js
```


## References

VSCode set up: https://www.youtube.com/watch?v=SnGwaRZ1Ci0


## Naming Branches
Categorize branches using prefixes like feature/, bugfix/, hotfix/, release/, or chore/. 

Example: feature/new-user-auth, bugfix/login-issue-123, hotfix/critical-prod-bug.