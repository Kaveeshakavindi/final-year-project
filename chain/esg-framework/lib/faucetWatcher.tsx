import Web3 from "web3";
import BN from "bn.js";
import FaucetABI from "../build/contracts/Faucet.json";
import {  ValueChangedEvent } from "@/types/types";

const FAUCET_CONTRACT_ADDRESS = "0x4071AE31Ac1b8617c93b3e1c3F399587eB46D1cE";
const ESG_DATA_SUBMISSION_CONTRACT_ADDRESS = "0x978BD43B57f2Aae8189e5EbA75b16beBe95c4E75"
export function startFaucetWatcher(callback: (data: ValueChangedEvent) => void) {
  const web3 = new Web3("http://127.0.0.1:8545");
  const contract = new web3.eth.Contract(FaucetABI.abi as any, FAUCET_CONTRACT_ADDRESS);
  
  //----faucet events---------
  contract.events
  //listens for all ValueChanged events from block 0 onward.
  //you get both past events (historical) and new ones in real time
    .ValueChanged({ fromBlock: 0 }) 
    .on("data", (event: any) => {

      //This is an object like { oldValue: "0", newValue: "42", caller: "0x..." }.
      //These come directly from the logs in the transaction receipt.
      const raw = event.returnValues;

      // Convert raw strings to BN
      const parsed: ValueChangedEvent = {
        //Converts the string into a BigNumber (BN) so 
        //I can safely do arithmetic without losing precision.
        oldValue: new BN(raw.oldValue.toString()),
        newValue: new BN(raw.newValue.toString()),
        caller: raw.caller,
      };

      //Sends this structured object back to your frontend, so you can, for example, update the UI when the value changes.
      callback(parsed);
    })
}
