import asyncio
import json
from SupervisorAgent import SupervisorAgent

if __name__ == "__main__":
    agent = SupervisorAgent()

    payload = json.dumps({
        "companyId": "121",
        "reportingPeriod": "Q1-2025",
        "kpiType": "POLLUTANTS_EMMISSION",
        "value": "320",
        "dataHash": "QmHash12345"
    })

    # Run async method
    result = asyncio.run(agent._execute_esgdata_contract(payload, "gpt-oss:latest"))
    print(result)
