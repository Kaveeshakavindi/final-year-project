ESG_ABI = [
    {
      "anonymous": False,
      "inputs": [
        {"indexed": False, "internalType": "uint256", "name": "submissionId", "type": "uint256"},
        {"indexed": False, "internalType": "string", "name": "companyId", "type": "string"},
        {"indexed": False, "internalType": "string", "name": "kpiType", "type": "string"},
        {"indexed": False, "internalType": "string", "name": "value", "type": "string"},
        {"indexed": False, "internalType": "string", "name": "dataHash", "type": "string"},
        {"indexed": True, "internalType": "address", "name": "submittedBy", "type": "address"},
        {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"}
      ],
      "name": "ESGDataSubmitted",
      "type": "event"
    },
    {
      "inputs": [
        {"internalType": "string", "name": "_companyId", "type": "string"},
        {"internalType": "string", "name": "_reportingPeriod", "type": "string"},
        {"internalType": "string", "name": "_kpiType", "type": "string"},
        {"internalType": "string", "name": "_value", "type": "string"},
        {"internalType": "string", "name": "_dataHash", "type": "string"}
      ],
      "name": "submitESGData",
      "outputs": [],
      "stateMutability": "nonpayable",
      "type": "function"
    },
    {
      "inputs": [
        {"internalType": "string", "name": "_companyId", "type": "string"}
      ],
      "name": "getCompanySubmissions",
      "outputs": [
        {
          "components": [
            {"internalType": "uint256", "name": "submissionId", "type": "uint256"},
            {"internalType": "string", "name": "companyId", "type": "string"},
            {"internalType": "string", "name": "reportingPeriod", "type": "string"},
            {"internalType": "string", "name": "kpiType", "type": "string"},
            {"internalType": "string", "name": "value", "type": "string"},
            {"internalType": "string", "name": "dataHash", "type": "string"},
            {"internalType": "address", "name": "submittedBy", "type": "address"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"}
          ],
          "internalType": "struct ESGDataSubmission.ESGData[]",
          "name": "",
          "type": "tuple[]"
        }
      ],
      "stateMutability": "view",
      "type": "function"
    }
]
