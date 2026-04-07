"use client";

import { useEffect, useState } from "react";
import { PageHeader, Metric, Card, Button, LevelBadge, EmptyState, SectionTitle } from "@/components/ui";
import { getLogStats, getOtelReceiverStatus, ingestLogs } from "@/lib/api";

const LOG_EXAMPLES: Record<string, string> = {
  "Payment service errors": `2025-11-14 09:31:02,456 ERROR payment_processor: InsufficientFundsError: balance 0 < amount 5000 for account acc_9912
  File "app/services/payment_processor.py", line 87, in process_payment
    raise InsufficientFundsError(...)
2025-11-14 09:31:45,123 ERROR ledger: LedgerError: currency mismatch GBP != USD for transfer txn_4421
2025-11-14 09:32:01,000 WARN  fraud_detector: High-risk score 0.91 for account acc_0033`,
  "Refund service errors": `2025-12-01 14:22:10,001 ERROR refund_service: RefundError: refund amount 10000 exceeds refundable 5000 for txn_1122
2025-12-01 14:22:55,445 WARN  refund_service: Transaction txn_3344 status not updated after partial refund`,
  "OTEL JSON": `{"timestamp": "2025-12-10T08:00:01Z", "level": "ERROR", "logger": "payment_processor", "message": "Race condition detected", "service": "payment-service", "traceId": "abc123"}`,
};

const INPUT_CLS =
  "w-full px-3.5 py-2.5 bg-bg-input border border-white/[0.09] rounded-xl text-[13px] text-text placeholder:text-text-dim focus:border-accent/40 focus:ring-2 focus:ring-accent/[0.07] outline-none transition-all";

export default function LogsPage() {
  const [logStatsData, setLogStatsData] = useState<Record<string, unknown>>({});
  const [otelStatus, setOtelStatus]     = useState<Record<string, unknown>>({});
  const [rawLogs, setRawLogs]           = useState("");
  const [serviceName, setServiceName]   = useState("payment-service");
  const [sourceFormat, setSourceFormat] = useState("raw");
  const [selectedExample, setSelectedExample] = useState("");
  const [ingesting, setIngesting]       = useState(false);
  const [result, setResult]             = useState<{ ok: boolean; text: string } | null>(null);

  function refresh() {
    getLogStats().then(setLogStatsData);
    getOtelReceiverStatus().then(setOtelStatus);
  }

  useEffect(refresh, []);

  useEffect(() => {
    if (selectedExample && LOG_EXAMPLES[selectedExample]) {
      setRawLogs(LOG_EXAMPLES[selectedExample]);
    }
  }, [selectedExample]);

  async function handleIngest() {
    if (!rawLogs.trim()) return;
    setIngesting(true);
    setResult(null);
    try {
      const res = await ingestLogs(rawLogs, serviceName, sourceFormat);
      setResult({
        ok:   !!res.ok,
        text: res.ok
          ? `Ingested ${(res.entries_ingested as number) ?? 0} entries`
          : res.error || "Failed",
      });
      refresh();
    } catch (err) {
      setResult({ ok: false, text: err instanceof Error ? err.message : "Unexpected error" });
    } finally {
      setIngesting(false);
    }
  }

  const total   = (logStatsData.total_entries as number) ?? 0;
  const byLevel = (logStatsData.by_level as Record<string, number>) ?? {};

  return (
    <>
      <PageHeader
        title="Log Ingest"
        subtitle="Logs are embedded alongside code — queryable in System Intelligence"
      />

      {/* OTEL Receiver */}
      <div className="grid lg:grid-cols-2 gap-5 mb-8">
        <Card>
          <div className="flex items-center justify-between mb-4">
            <div className="text-[14px] font-semibold text-text-bright">OpenTelemetry Receiver</div>
            {!!otelStatus.ok && (
              <span
                className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${
                  otelStatus.enabled
                    ? "text-success bg-success/[0.08] border-success/20"
                    : "text-warning bg-warning/[0.08] border-warning/20"
                }`}
              >
                {otelStatus.enabled ? "Active" : "Disabled"}
              </span>
            )}
          </div>
          {otelStatus.ok ? (
            <div className="grid grid-cols-4 gap-3">
              <Metric label="Requests"  value={((otelStatus.total_requests_received as number) ?? 0).toLocaleString()} />
              <Metric label="Records"   value={((otelStatus.total_log_records_received as number) ?? 0).toLocaleString()} />
              <Metric label="Ingested"  value={((otelStatus.total_entries_ingested as number) ?? 0).toLocaleString()} />
              <Metric label="Filtered"  value={((otelStatus.total_dropped as number) ?? 0).toLocaleString()} />
            </div>
          ) : (
            <div className="text-[12.5px] text-text-dim">Could not fetch OTEL status.</div>
          )}
        </Card>

        <Card className="bg-info/[0.03] border-info/[0.14]">
          <div className="text-[14px] font-semibold text-text-bright mb-3">OTEL Endpoint</div>
          <div className="text-[12.5px] text-text-muted mb-3 leading-relaxed">
            Point your OTEL Collector or SDK exporter at:
          </div>
          <code className="text-[12px] text-accent font-mono">
            POST http://&lt;rootops-host&gt;:8000/v1/logs
          </code>
          <pre className="text-[11px] text-text-muted mt-4 bg-[#06060A] border border-white/[0.06] p-3.5 rounded-xl font-mono">
{`exporters:
  otlphttp:
    endpoint: http://rootops-api:8000`}
          </pre>
        </Card>
      </div>

      {/* Active filters */}
      <div className="mb-8">
        <SectionTitle>Active Filters</SectionTitle>
        <div className="grid grid-cols-5 gap-3">
          <Metric label="Min Severity" value="WARN"    />
          <Metric label="Allowlist"    value="All"     />
          <Metric label="Dedup Window" value="60s"     />
          <Metric label="Max Message"  value="2000"    />
          <Metric label="Rate Limit"   value="500/hr"  />
        </div>
      </div>

      <div className="h-px bg-white/[0.05] mb-8" />

      {/* Manual ingest */}
      <div className="mb-8">
        <SectionTitle>Manual Ingest</SectionTitle>

        <div className="grid lg:grid-cols-4 gap-5">
          <div className="lg:col-span-3">
            <textarea
              value={rawLogs}
              onChange={(e) => setRawLogs(e.target.value)}
              placeholder="Paste log output here…"
              className="w-full h-52 px-4 py-3 bg-bg-input border border-white/[0.09] rounded-xl text-[12px] text-text font-mono placeholder:text-text-dim focus:border-accent/40 focus:ring-2 focus:ring-accent/[0.07] outline-none resize-none transition-all"
            />
          </div>
          <div className="space-y-3">
            <div>
              <label className="block text-[11px] font-medium text-text-dim mb-1.5">Service name</label>
              <input
                type="text"
                placeholder="payment-service"
                value={serviceName}
                onChange={(e) => setServiceName(e.target.value)}
                className={INPUT_CLS}
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-text-dim mb-1.5">Format</label>
              <select
                value={sourceFormat}
                onChange={(e) => setSourceFormat(e.target.value)}
                aria-label="Log format"
                className={INPUT_CLS}
              >
                <option value="raw">raw</option>
                <option value="otel">otel</option>
                <option value="file">file</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-medium text-text-dim mb-1.5">Load example</label>
              <select
                value={selectedExample}
                onChange={(e) => setSelectedExample(e.target.value)}
                aria-label="Load example logs"
                className={INPUT_CLS}
              >
                <option value="">— paste your own —</option>
                {Object.keys(LOG_EXAMPLES).map((k) => (
                  <option key={k} value={k}>{k}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-4">
          <Button type="button" onClick={handleIngest} disabled={ingesting || !rawLogs.trim()}>
            {ingesting ? "Ingesting…" : "Ingest logs"}
          </Button>
          {result && (
            <span className={`text-[12.5px] font-medium ${result.ok ? "text-success" : "text-error"}`}>
              {result.ok ? "✓ " : "✗ "}{result.text}
            </span>
          )}
        </div>
      </div>

      <div className="h-px bg-white/[0.05] mb-8" />

      {/* Stats */}
      <div>
        <SectionTitle>Aggregate Stats</SectionTitle>
        {!logStatsData.ok ? (
          <Card>
            <EmptyState
              title="No logs yet"
              description="Ingest logs above or connect an OTEL source."
            />
          </Card>
        ) : (
          <div className="flex flex-wrap items-center gap-5">
            <Metric label="Total" value={total.toLocaleString()} accent />
            {Object.entries(byLevel)
              .sort()
              .map(([level, count]) => (
                <div key={level} className="flex items-center gap-2.5">
                  <LevelBadge level={level} />
                  <span className="text-[13px] font-semibold text-text">
                    {(count as number).toLocaleString()}
                  </span>
                </div>
              ))}
          </div>
        )}
      </div>
    </>
  );
}
