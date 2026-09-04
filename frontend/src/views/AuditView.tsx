import React, { useState, useEffect } from "react";
import { api } from "../api";
import type { AuditLog } from "../types";
import { playTacticalTone, fmtTime } from "../utils/audio";

function Empty({ text }: { text: string }) {
  return (
    <div style={{ textAlign: "center", padding: "40px 10px", color: "var(--text-ghost)", fontSize: 12 }}>
      {text}
    </div>
  );
}

export function AuditView() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [chainValid, setChainValid] = useState<boolean | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    api.auditLogs().then(setLogs).catch(() => {});
  }, []);

  const verifyChain = async () => {
    setVerifying(true);
    playTacticalTone('click');
    try {
      const res = await api.verifyAudit();
      setChainValid(res.chain_valid);
      playTacticalTone(res.chain_valid ? 'verify' : 'alert');
    } catch {
      setChainValid(false);
      playTacticalTone('alert');
    }
    setVerifying(false);
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Tamper-Proof Military Audit Ledger</h1>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)' }}>
            Cryptographically chained immutable ledger recording all officer and AI system actions
          </p>
        </div>
        <button className="btn btn-primary" onClick={verifyChain} disabled={verifying}>
          {verifying ? 'Verifying Hash Chain...' : '🔗 Verify Chain Integrity'}
        </button>
      </div>

      {chainValid !== null && (
        <div className={`test-feedback ${chainValid ? 'success' : 'fail'}`} style={{ marginBottom: 16 }}>
          {chainValid ? '✓ IMMUTABLE AUDIT CHAIN 100% VALID — ZERO TAMPERING DETECTED' : '✕ AUDIT CHAIN INTEGRITY CORRUPTED'}
        </div>
      )}

      {logs.length === 0 ? (
        <Empty text="Audit ledger empty." />
      ) : (
        <div className="blockchain-ledger-view">
          {logs.map((l) => (
            <div key={l.id} className="blockchain-block">
              <div className="block-index-badge">
                <span style={{ fontSize: 9, color: 'var(--text-ghost)' }}>BLOCK</span>
                <span>#{l.id}</span>
              </div>
              <div className="block-data-col">
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 2 }}>
                  <b style={{ color: '#fff', fontSize: 13 }}>{l.action}</b>
                  <span className="reason-tag" style={{ background: 'rgba(0, 240, 255, 0.1)', color: '#00f0ff' }}>
                    {l.actor} ({l.role})
                  </span>
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-ghost)', fontFamily: 'var(--font-mono)' }}>
                    {fmtTime(l.created_at)}
                  </span>
                </div>
                <div className="block-hash-pipe">
                  <span>PREV: <span className="hash-token">{l.previous_hash ? l.previous_hash.substring(0, 16) : 'GENESIS'}…</span></span>
                  <span>→</span>
                  <span>HASH: <span className="hash-token">{l.record_hash?.substring(0, 16)}…</span></span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ─── Health & Edge Diagnostics ───────────────────────────────── */
