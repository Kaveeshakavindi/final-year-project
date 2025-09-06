"use client"
import { useEffect, useState } from "react";
import { startFaucetWatcher } from '../lib/faucetWatcher'
import { ValueChangedEvent } from "@/types/types";
import BN from "bn.js";

export default function Home() {
  const [value, setValue] = useState<BN | undefined>();

  useEffect(() => {
    startFaucetWatcher((data: ValueChangedEvent) => setValue(data.newValue));
  }, [value]);

  return (
    <div className="font-sans grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20">
      <h1>Faucet Value: {value?.toString() || 'Loading...'}</h1>
    </div>
  );
}