// types.ts
import BN from "bn.js";

export interface ValueChangedEvent {
  oldValue: BN;     // or string if you don't want BN
  newValue: BN;     // or string
  caller: string;
}

//data submission event type
export type ESGDataEvent = {
  submissionId: string;
  companyId: string;
  reportingPeriod: string;
  kpiType: string;
  value: string;
  dataHash: string;
  submittedBy: string;
  timestamp: any;
}