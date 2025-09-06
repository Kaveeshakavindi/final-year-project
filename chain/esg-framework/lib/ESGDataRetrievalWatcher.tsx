import Web3 from "web3";
import ESGSubmissionABI from "../build/contracts/ESGDataSubmission.json"
import { ESGDataEvent } from "@/types/types";

const ESG_DATA_SUBMISSION_CONTRACT_ADDRESS = "0x978BD43B57f2Aae8189e5EbA75b16beBe95c4E75"
export function startESGDataRetrievalWatcher(callback: (data: ESGDataEvent) => void) {
  const web3 = new Web3("http://127.0.0.1:8545");
  const esg_data_submission_contract = new web3.eth.Contract(ESGSubmissionABI.abi as any, ESG_DATA_SUBMISSION_CONTRACT_ADDRESS)
 
  esg_data_submission_contract.events
    .ESGDataSubmitted({ fromBlock: 0 }) 
    .on("data", (event: any) => {
      const raw = event.returnValues;
      const parsed_esg_data_submission: ESGDataEvent = {
        submissionId: raw.submissionId,
        companyId: raw.companyId,
        reportingPeriod: raw.reportingPeriod,
        kpiType: raw.kpiType,
        value: raw.value,
        dataHash: raw.dataHash,
        submittedBy: raw.submittedBy,
        timestamp: raw.timestamp,
      };
      callback(parsed_esg_data_submission);
    })
}
