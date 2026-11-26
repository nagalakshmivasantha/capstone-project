import { Badge, Card, Empty, Plot, Tile, missingTone, percent, scoreTone, severityTone } from './ui';

export function Overview({ summary, trends, alerts }) {
  const datasets = summary?.datasets || [];
  const overview = summary?.quality_overview || {};
  const ready = overview.datasets_ready || 0;
  const total = summary?.metrics?.datasets_registered || 0;
  const alertCount = alerts.filter(alert => alert.severity !== 'INFO').length;
  const blocked = overview.issues > 0 || overview.datasets_with_ml_safety_issues > 0 || alerts.some(alert => alert.severity === 'CRITICAL');
  const clear = total > 0 && ready === total && overview.leakage_pass;
  const score = overview.overall_score;
  const tone = scoreTone(score);
  const missing = new Map();
  for (const quality of summary?.quality || []) {
    for (const [column, amount] of Object.entries(quality.null_percent_by_column || {})) {
      missing.set(column, Math.max(missing.get(column) || 0, Number(amount)));
    }
  }
  const highest = [...missing].sort((a, b) => b[1] - a[1]).slice(0, 12);
  const counts = { CSV: 0, Parquet: 0, Other: 0 };
  for (const dataset of datasets) {
    const format = String(dataset.format).toLowerCase();
    counts[format === 'csv' ? 'CSV' : format === 'parquet' ? 'Parquet' : 'Other']++;
  }
  const quality = trends?.quality_score || [];
  const leakage = trends?.leakage_issues || [];

  return <section id="overview" className="section">
    <div className="gateway-banner">
      <div className="shield" aria-hidden="true">🛡️</div>
      <div><h2>ML Feature Retrieval Safety Gate <span className={`tag ${blocked ? 'blocked' : clear ? 'safe' : 'warn'}`}>
        {!summary ? 'PENDING' : blocked ? 'REPAIRS PENDING' : clear ? 'ALL CLEAR' : 'WATCH'}
      </span></h2></div>
      <div className="gateway-meta">
        <Tile label="Score" value={percent(score)} />
        <Tile label="Leakage" value={summary ? overview.leakage_pass ? 'PASS' : 'FAIL' : '—'} />
        <Tile label="Datasets" value={summary ? `${ready}/${total}` : '—'} />
      </div>
    </div>
    <div className="grid-4">
      <Metric label="Overall Quality Score" note={overview.status || 'Awaiting telemetry'}>
        {percent(score)} {score != null && <Badge tone={tone}>{({ good: 'GOOD', warn: 'WATCH', crit: 'FAIL' })[tone]}</Badge>}
      </Metric>
      <Metric label="Temporal Leakage Gate" note={summary ? `${overview.issues || 0} issue(s) detected` : 'Historical join safety'}>
        {summary ? <Badge tone={overview.leakage_pass ? 'good' : 'crit'}>{overview.leakage_pass ? 'PASS' : 'FAIL'}</Badge> : '—'}
      </Metric>
      <Metric label="Datasets Ready" note={summary ? `${ready} of ${total} passed the gateway` : ''}>{summary ? ready : '—'}</Metric>
      <Metric label="Active Alerts" note="Risk signals awaiting action">{summary ? alertCount : '—'}</Metric>
    </div>
    <div className="grid-2">
      <Card title="📈 Quality Score — Recent Evaluations">
        <Plot title="Quality scores by evaluation" type="line" labels={quality.map(p => p.period)}
          series={[{ label: 'Quality score', values: quality.map(p => Number(p.value)), color: '#6aa0ff' }]} suffix="%" min={0} max={100} />
      </Card>
      <Card title="⚠️ Leakage & Issue Trend">
        <Plot title="Blocking issues by evaluation" type="line" labels={leakage.map(p => p.period)}
          series={[{ label: 'Blocking issues', values: leakage.map(p => Number(p.value)), color: '#f46e74' }]} min={0} />
      </Card>
      <Card title="📊 Missing Values by Column">
        <Plot title="Maximum missing percentage by column" labels={highest.map(([label]) => label)}
          series={[{ label: 'Maximum missing', values: highest.map(([, value]) => value),
            color: highest.map(([, value]) => ({ crit: '#f46e74', warn: '#f2b844', good: '#3fd59a' })[missingTone(value)]) }]} suffix="%" />
      </Card>
      <Card title="🎯 Format Distribution">
        <Plot title="Registered datasets by format" type="doughnut" labels={Object.keys(counts)}
          series={[{ values: Object.values(counts), color: ['#6aa0ff', '#4dd6e8', '#b086ff'] }]} legend />
      </Card>
    </div>
  </section>;
}

function Metric({ label, note, children }) {
  return <div className="card"><div className="kpi-label">{label}</div><div className="kpi">{children}</div>
    <div className="kpi-meta">{note}</div></div>;
}

export function Inventory({ summary, onInspect }) {
  const datasets = summary?.datasets || [];
  const qualityById = new Map((summary?.quality || []).map(item => [item.dataset_id, item]));
  return <section id="datasets" className="section">
    <Card title="📦 Dataset Inventory & Quality Posture"
      action={<a className="button-link" href="#uploadSection">+ Connect dataset</a>}>
      <div className="kpi-row">
        <Tile label="Registered" value={summary?.metrics?.datasets_registered} />
        <Tile label="Ready for ML" value={summary?.quality_overview?.datasets_ready} />
        <Tile label="Cache Entries" value={summary?.metrics?.cache_entries} />
        <Tile label="Evidence Query" value={summary?.evidence?.query_id} />
      </div>
      {datasets.length > 0 ? <div className="table-scroll"><table>
        <thead><tr>{['Dataset', 'Rows', 'Columns', 'Format', 'Quality', 'Issues', 'ML Ready', 'Action'].map(label => <th key={label}>{label}</th>)}</tr></thead>
        <tbody>{datasets.map(dataset => {
          const safe = dataset.quality_score >= 80 && qualityById.get(dataset.dataset_id)?.ml_safe;
          return <tr key={dataset.dataset_id}>
          <td><b>{dataset.dataset_id}</b> {dataset.repaired_from && <Badge>REPAIRED</Badge>}</td>
          <td>{(dataset.rows || 0).toLocaleString()}</td>
          <td>{dataset.columns?.length || dataset.columns_num || 0}</td>
          <td><Badge>{String(dataset.format || '—').toUpperCase()}</Badge></td>
          <td><Badge tone={scoreTone(dataset.quality_score)}>{percent(dataset.quality_score)}</Badge></td>
          <td>{dataset.rule_count || 0}</td>
          <td><Badge tone={safe ? 'good' : 'crit'}>{safe ? 'SAFE' : 'BLOCKED'}</Badge></td>
          <td><button className="btn-mini primary" onClick={() => onInspect(dataset.dataset_id)}>Inspect</button></td>
        </tr>;
        })}</tbody>
      </table></div> : <Empty>{summary ? 'No datasets yet. Upload one below.' : 'Dataset inventory is unavailable.'}</Empty>}
    </Card>
  </section>;
}

function AcceptanceList({ tests }) {
  return tests.length ? tests.map((test, index) => <div className="alert-item" key={`${test.test_id}-${index}`}>
    <Badge tone={test.pass ? 'good' : 'crit'}>{test.pass ? 'PASS' : 'FAIL'}</Badge>
    <div className="body"><strong>{test.test_id}</strong><small>{test.condition}<br />
      Expected {test.expected_result} · Observed {test.observed_result}</small></div>
  </div>) : <Empty>No acceptance tests.</Empty>;
}

function bytes(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1048576) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / 1048576).toFixed(2)} MB`;
}

export function Reports({ alerts, acceptance, storage, evidence, inspection }) {
  const tests = acceptance?.negative_tests || [];
  const objects = storage?.objects || [];
  return <>
    <section id="alerts" className="section grid-2">
      <Card title="🚨 Alert Timeline">
        {alerts.length ? alerts.map((alert, index) => <div className="alert-item" key={`${alert.title}-${index}`}>
          <Badge tone={severityTone(alert.severity)}>{alert.severity}</Badge>
          <div className="body"><strong>{alert.title}</strong><small>{alert.detail} · {alert.source || 'quality-gateway'}</small></div>
        </div>) : <Empty>No alerts reported.</Empty>}
      </Card>
      <Card title="🛡️ Governance Acceptance Suite"><AcceptanceList tests={tests} /></Card>
    </section>
    <section id="lineage" className="section">
      <Card title="🔗 Lineage & Evidence Manifest">
        <div className="kpi-row">
          <Tile label="Evidence Query" value={evidence?.query_id} />
          <Tile label="Selected Dataset" value={inspection?.dataset_id || inspection?.registration?.dataset_id} />
          <Tile label="Source" value={inspection?.lineage?.source} />
        </div>
      </Card>
    </section>
    <section id="storage" className="section">
      <Card title="💾 Object Storage — MinIO">
        {storage?.error ? <Empty>{storage.error}</Empty> : objects.length ? objects.map(object => <div className="obj-row" key={`${object.bucket}/${object.object_name}`}>
          <span className="obj-name">{object.bucket || 'features'}/{object.object_name}</span>
          <span className="obj-meta">{bytes(object.size_bytes || 0)}</span>
        </div>) : <Empty>No objects uploaded yet.</Empty>}
      </Card>
    </section>
    <section id="governance" className="section">
      <Card title="🛡️ Governance Gates — Acceptance Tests">
        <div className="kpi-row">
          <Tile label="Suite status" value={acceptance?.status} />
          <Tile label="Tests run" value={tests.length} />
          <Tile label="Improved join correctness" value={acceptance?.improved?.join_correctness == null ? '—' : percent(acceptance.improved.join_correctness * 100, 0)} />
          <Tile label="Improved leakage score" value={acceptance?.improved?.leakage_score} />
        </div>
        <AcceptanceList tests={tests} />
      </Card>
    </section>
  </>;
}
