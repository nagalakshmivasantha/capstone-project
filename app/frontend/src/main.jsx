import { useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { datasetPath, request, safetyFor } from './api';
import { Overview, Inventory, Reports } from './Overview';
import { Inspection } from './Inspection';
import { Card, percent } from './ui';
import './styles.css';

const navigation = [
  ['overview', '⚡ Overview & safety'], ['datasets', '📦 Datasets'],
  ['inspect', '🔍 Inspect & repair'], ['alerts', '🚨 Alerts'],
  ['lineage', '🔗 Lineage & evidence'], ['storage', '💾 Object storage'],
  ['governance', '🛡️ Governance gates'],
];

function Upload({ busy, status, onUpload }) {
  return <section id="uploadSection" className="section">
    <Card title="⬆️ Connect a Dataset">
      <form className="upload-form" onSubmit={onUpload}>
        <label>Dataset ID <span className="muted">(optional)</span>
          <input name="dataset_id" placeholder="e.g. customer_income_features" />
        </label>
        <label>CSV or Parquet file
          <input name="file" type="file" accept=".csv,.parquet" required />
        </label>
        <div><button type="submit" className="primary" disabled={busy}>Upload &amp; Evaluate Safety</button></div>
      </form>
      <div role="status" className={`status-line ${status?.tone || ''}`}>
        {status?.text || 'Upload a dataset to check its quality and ML retrieval safety.'}
      </div>
    </Card>
  </section>;
}

function Dashboard() {
  const [snapshot, setSnapshot] = useState(null);
  const [refreshError, setRefreshError] = useState('');
  const [interval, setIntervalMs] = useState(0);
  const [revision, setRevision] = useState(0);
  const [section, setSection] = useState(() => location.hash.slice(1) || 'overview');
  const [selected, setSelected] = useState('');
  const [inspection, setInspection] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [repairStatus, setRepairStatus] = useState(null);
  const [busy, setBusy] = useState(false);
  const refreshRequest = useRef(null);

  const refresh = useCallback(async () => {
    refreshRequest.current?.abort();
    const controller = new AbortController();
    refreshRequest.current = controller;
    const options = { signal: controller.signal };
    try {
      const [summary, trends, alerts, storage] = await Promise.all([
        request('/dashboard/summary', options),
        request('/dashboard/trends', options),
        request('/dashboard/alerts', options),
        request('/storage/minio/objects', options).catch(error => ({ error: error.message })),
      ]);
      if (controller.signal.aborted) return;
      setSnapshot({ summary, trends, alerts: alerts.alerts || [], storage });
      setRefreshError('');
      setRevision(value => value + 1);
    } catch (error) {
      if (!controller.signal.aborted) setRefreshError(error.message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const syncSection = () => setSection(location.hash.slice(1) || 'overview');
    window.addEventListener('hashchange', syncSection);
    return () => {
      refreshRequest.current?.abort();
      window.removeEventListener('hashchange', syncSection);
    };
  }, [refresh]);

  useEffect(() => {
    if (!interval) return;
    const timer = setInterval(refresh, interval);
    return () => clearInterval(timer);
  }, [refresh, interval]);

  useEffect(() => {
    if (!selected) return;
    const controller = new AbortController();
    request(datasetPath(selected, 'detail'), { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setInspection({ id: selected, data }); })
      .catch(error => { if (!controller.signal.aborted) setInspection({ id: selected, error: error.message }); });
    return () => controller.abort();
  }, [selected, revision]);

  function select(id) {
    if (id !== selected) setInspection(null);
    setSelected(id);
  }

  function inspect(id) {
    select(id);
    location.hash = 'inspect';
  }

  async function upload(event) {
    event.preventDefault();
    if (busy) return;
    const form = event.currentTarget;
    const body = new FormData(form);
    const id = String(body.get('dataset_id') || '').trim();
    if (id) body.set('dataset_id', id);
    else body.delete('dataset_id');
    setBusy(true);
    setUploadStatus({ text: 'Uploading, profiling, and evaluating safety…' });
    try {
      const result = await request('/dashboard/datasets/upload', { method: 'POST', body });
      const dataset = result.persistence?.dataset_id || result.registration?.dataset_id;
      const safety = safetyFor(result.quality);
      const decision = safety.safe_for_feature_retrieval ? 'Safe for ML feature retrieval' : `Blocked pending repair (${safety.issue_count} issues)`;
      setUploadStatus({ tone: 'ok', text: `Uploaded ${dataset || 'dataset'}. ${decision}. Quality score ${percent(result.quality?.quality?.quality_score)}.` });
      form.reset();
      if (dataset) inspect(dataset);
      await refresh();
    } catch (error) {
      setUploadStatus({ tone: 'err', text: `Upload failed: ${error.message}` });
    } finally {
      setBusy(false);
    }
  }

  async function repair(column, method, segmentColumn) {
    if (busy || !selected) return;
    setBusy(true);
    setRepairStatus({ text: `Applying ${method} to ${column} in ${selected}…` });
    try {
      const result = await request(datasetPath(selected, 'repair'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ column, method, ...(segmentColumn && { segment_column: segmentColumn }) }),
      });
      setRepairStatus({ tone: 'ok', text: `Repair applied to ${column}. Quality ${percent(result.before?.quality_score)} → ${percent(result.after?.quality_score)}. ${result.after?.decision || ''}` });
      if (result.repaired_dataset_id) inspect(result.repaired_dataset_id);
      await refresh();
    } catch (error) {
      setRepairStatus({ tone: 'err', text: `Repair failed: ${error.message}` });
    } finally {
      setBusy(false);
    }
  }

  const { summary, trends, alerts = [], storage } = snapshot || {};
  const current = inspection?.id === selected ? inspection : null;
  return <div className="app">
    <aside>
      <div className="brand"><div className="brand-logo">QG</div>quality<b>gateway</b></div>
      <div className="nav-section">ML Safety Workflow</div>
      <nav aria-label="Dashboard sections">
        {navigation.map(([id, label]) => <a key={id} href={`#${id}`}
          aria-current={id === section ? 'location' : undefined} className={id === section ? 'active' : ''}>{label}</a>)}
      </nav>
    </aside>
    <main>
      <div className="topbar">
        <div><h1>Intelligent Quality Gateway</h1><div className="sub">ML Feature Retrieval Safety &amp; Automated Repair</div></div>
        <div className="actions">
          <span role="status" className={`live-indicator ${refreshError ? 'offline' : ''}`}><i className="pulse" />
            {refreshError ? 'Unavailable' : snapshot ? 'Live' : 'Connecting…'}
          </span>
          <select aria-label="Refresh interval" value={interval} onChange={event => setIntervalMs(Number(event.target.value))}>
            <option value={0}>Manual refresh</option><option value={30000}>Refresh every 30s</option><option value={60000}>Refresh every 60s</option>
          </select>
          <button onClick={refresh}>🔄 Refresh</button>
        </div>
      </div>
      {refreshError && <p role="alert" className="status-line err">Dashboard refresh failed: {refreshError}</p>}
      <Overview summary={summary} trends={trends} alerts={alerts} />
      <Inventory summary={summary} onInspect={inspect} />
      <Upload busy={busy} status={uploadStatus} onUpload={upload} />
      <Inspection datasets={summary?.datasets || []} selected={selected} onSelect={select} detail={current?.data}
        error={current?.error} onRepair={repair} repairStatus={repairStatus} busy={busy} />
      <Reports alerts={alerts} acceptance={summary?.acceptance} evidence={summary?.evidence}
        storage={storage} inspection={current?.data} />
    </main>
  </div>;
}

createRoot(document.getElementById('root')).render(<Dashboard />);
