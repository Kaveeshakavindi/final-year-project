const Faucet = artifacts.require("Faucet");

module.exports = function (deployer) {
  deployer.deploy(Faucet, { gas: 3000000 });
};