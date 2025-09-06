"use client";
import { useEffect, useState } from "react";
import { startESGDataRetrievalWatcher } from "../../lib/ESGDataRetrievalWatcher";
import { ESGDataEvent } from "@/types/types";

export default function ESGDataDashboard() {
  const [submissions, setSubmissions] = useState<ESGDataEvent[]>([]);

  useEffect(() => {
    startESGDataRetrievalWatcher((data) => {
      setSubmissions((prev) => [...prev, data]); // append new submission
    });
  }, []);

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">ESG Submissions</h1>
      <ul className="space-y-2">
        {submissions.map((s) => (
          <li key={s.submissionId} className="border p-2 rounded">
            <p><strong>Company:</strong> {s.companyId}</p>
            <p><strong>Reporting Period:</strong> {s.reportingPeriod}</p>
            <p><strong>KPI:</strong> {s.kpiType}</p>
            <p><strong>Value:</strong> {s.value}</p>
            <p><strong>Data Hash:</strong> {s.dataHash}</p>
            <p><strong>Submitted By:</strong> {s.submittedBy}</p>
            {/* <p><strong>Timestamp:</strong> {new Date(s.timestamp * 1000).toLocaleString()}</p> */}
          </li>
        ))}
      </ul>
    </div>
  );
}
