// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.21;

/// @title ESG Data Submission Contract
/// @notice Allows investee companies and investment managers to submit ESG KPI data
/// @dev Stores only metadata & IPFS/Arweave hashes on-chain to save gas

contract ESGDataSubmission {
    // -----------------
    // STRUCTS & STORAGE
    // -----------------
    
    struct ESGData {
        uint256 submissionId;
        string companyId;         // e.g. unique identifier for company (could be LEI code)
        string reportingPeriod;   // e.g. "Q1-2025" or "2025"
        string kpiType;           // e.g. "CO2_Emissions", "Diversity_Ratio"
        string value;             // value as string (could be numeric or percentage)
        string dataHash;          // IPFS/Arweave hash of detailed ESG report
        address submittedBy;      // company or investment manager wallet
        uint256 timestamp;        // block timestamp of submission
    }

    // Auto-incremented submission counter
    uint256 private submissionCounter;

    // Mapping submissionId → ESGData
    mapping(uint256 => ESGData) public submissions;

    // Mapping companyId → array of submissionIds
    mapping(string => uint256[]) private companySubmissions;

    // -----------------
    // EVENTS
    // -----------------
    event ESGDataSubmitted(
        uint256 submissionId,
        string companyId,
        string kpiType,
        string value,
        string dataHash,
        address indexed submittedBy,
        uint256 timestamp
    );

    // -----------------
    // FUNCTIONS
    // -----------------

    /// @notice Submit ESG KPI data
    /// @param _companyId Unique identifier for the company
    /// @param _reportingPeriod Time period (e.g. "Q1-2025")
    /// @param _kpiType KPI type (e.g. "CO2_Emissions")
    /// @param _value KPI value (string to allow numbers, ratios, %)
    /// @param _dataHash Off-chain IPFS/Arweave hash of the full dataset/report
    function submitESGData(
        string memory _companyId,
        string memory _reportingPeriod,
        string memory _kpiType,
        string memory _value,
        string memory _dataHash
    ) external {
        submissionCounter++;

        ESGData memory newSubmission = ESGData({
            submissionId: submissionCounter,
            companyId: _companyId,
            reportingPeriod: _reportingPeriod,
            kpiType: _kpiType,
            value: _value,
            dataHash: _dataHash,
            submittedBy: msg.sender,
            timestamp: block.timestamp
        });

        submissions[submissionCounter] = newSubmission;
        companySubmissions[_companyId].push(submissionCounter);

        emit ESGDataSubmitted(
            submissionCounter,
            _companyId,
            _kpiType,
            _value,
            _dataHash,
            msg.sender,
            block.timestamp
        );
    }

    /// @notice Retrieve all submissions for a given company
    /// @param _companyId The company identifier
    /// @return Array of ESGData for that company
    function getCompanySubmissions(string memory _companyId)
        external
        view
        returns (ESGData[] memory)
    {
        uint256[] memory ids = companySubmissions[_companyId];
        ESGData[] memory results = new ESGData[](ids.length);

        for (uint256 i = 0; i < ids.length; i++) {
            results[i] = submissions[ids[i]];
        }
        return results;
    }
}
// truffle compile --reset
// truffle migrate --reset
// const t = await ESGDataSubmission.deployed()
// await t.submitESGData("121", "Q1-2025", "POLLUTANTS_EMMISSION", "320", "QmHash12345", {from: accounts[0]})
// let allevents = await t.getPastEvents('ESGDataSubmitted', {fromBlock: 0, toBlock: 'latest'})
// console.log(allevents.map(e => e.returnValues))

//get contract address
//given deployed contract => esg (const esg = await ESGDataSubmission.deployed())
//esg.address