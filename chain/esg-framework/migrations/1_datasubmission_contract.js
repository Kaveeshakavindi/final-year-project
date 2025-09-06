const ESGDataSubmission = artifacts.require("ESGDataSubmission");

module.exports = function (deployer) {
  deployer.deploy(ESGDataSubmission, { gas: 3000000 });
};