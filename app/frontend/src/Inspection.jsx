import { useState } from 'react';
import { safetyFor } from './api';
import { Badge, Card, Empty, Plot, Tile, missingTone, percent, severityTone } from './ui';

const percentileKeys = ['p1', 'p5', 'p10', 'p25', 'p50', 'p75', 'p90', 'p95', 'p99'];

function Histogram({ column, distribution, size }) {
  const bins = distribution.histogram;
  return <Plot title={`Distribution of ${column}`} size={size} labels={bins.map(bin => String(bin.bin_start))}
    series={[{ label: 'Row count', values: bins.map(bin => bin.count), color: '#4dd6e8' }]} />;
}

function Distribution({ column, data }) {
  const stats = data.stats || data;
  const percentile = data.percentiles || data;
  return <div className="grid-2">
    <Card title={`Distribution of ${column}`}><Histogram column={column} distribution={data} size="lg" /></Card>
    <Card title="Distribution statistics">
      <div className="kpi-row">
        <Tile label="Skew" value={data.skew?.toFixed(2)} />
        <Tile label="Kurtosis" value={data.kurtosis?.toFixed(2)} />
        <Tile label="Outliers (IQR)" value={(data.outliers?.low_count || 0) + (data.outliers?.high_count || 0)} />
        <Tile label="Min" value={stats.min} /><Tile label="P25" value={percentile.p25} />
        <Tile label="Median" value={percentile.p50 ?? stats.median} /><Tile label="P75" value={percentile.p75} />
        <Tile label="Max" value={stats.max} />
      </div>
      <h3>Percentiles</h3>
      <Plot title={`Percentiles for ${column}`} labels={percentileKeys.map(key => key.toUpperCase())}
        series={[{ label: 'Value', values: percentileKeys.map(key => percentile[key] ?? (key === 'p50' ? stats.median : null)), color: '#b086ff' }]} />
    </Card>
  </div>;
}

const segmentLabel = segment => String(segment.segment ?? segment.segment_value ?? '');

function SegmentTable({ analysis }) {
  return <div className="table-scroll segment-stats"><table>
    <thead><tr><th>{analysis.segment_column || 'Segment'}</th><th>Missing</th><th>Median</th><th>Mean</th><th>Missing / total</th></tr></thead>
    <tbody>{analysis.segments.map((segment, index) => <tr key={index}>
      <td>{segmentLabel(segment)}</td>
      <td><Badge tone={missingTone(segment.missing_percent)}>{percent(segment.missing_percent)}</Badge></td>
      <td>{segment.median ?? '—'}</td><td>{segment.mean ?? '—'}</td>
      <td>{segment.missing_count || 0} / {segment.total ?? segment.total_count ?? 0}</td>
    </tr>)}</tbody>
  </table></div>;
}

function SegmentCharts({ issue }) {
  const analysis = issue.segment_analysis;
  const labels = analysis.segments.map(segmentLabel);
  return <div className="grid-2">
    <Card title={`Missingness by ${analysis.segment_column || 'segment'}`} note={`Spread ${percent(analysis.spread_percent, 0)}`}>
      <Plot title="Missing percentage by segment" labels={labels} suffix="%"
        series={[{ label: 'Missing %', values: analysis.segments.map(segment => segment.missing_percent), color: '#f2b844' }]} />
      <SegmentTable analysis={analysis} />
    </Card>
    <Card title="Median by segment">
      <Plot title="Median values by segment" labels={labels}
        series={[{ label: 'Median', values: analysis.segments.map(segment => segment.median), color: '#3fd59a' }]} />
    </Card>
  </div>;
}

function repairMethod(name) {
  name = name.toLowerCase();
  if (name.includes('mean')) return 'mean';
  if (name.includes('segment')) return 'segment_median';
  if (name.includes('median')) return 'median';
  if (name.includes('drop')) return 'drop';
  return null;
}

function Issue({ issue, onRepair, busy }) {
  const distribution = issue.distribution;
  const segments = issue.segment_analysis;
  return <div className="issue-card">
    <div className="issue-head">
      <h3>{issue.column} <span className="muted">/ {issue.missing_percent ? `${issue.missing_percent}% missing` : `${issue.impact_percent || 0}% of rows affected`}</span></h3>
      <Badge tone={severityTone(issue.severity)}>{issue.severity || 'QUALITY ISSUE'}</Badge>
    </div>
    <div className="char-tags">{(issue.characteristics || []).map(tag => <span className="chip" key={tag}>{tag}</span>)}</div>
    {(issue.options || []).length > 0 && <>
      <h3>Possible Repair Strategies</h3>
      <div className="repair-grid">{issue.options.map((option, index) => {
        const method = repairMethod(option.name);
        const recommended = option.name === issue.recommended ||
          (option.name === 'Segment median' && issue.recommended === 'Segment-level median');
        const risk = option.risk?.toLowerCase();
        return <div key={index} className={`repair-opt ${recommended ? 'rec' : ''}`}>
          <b>{option.name} {risk && <Badge tone={risk}>Risk {option.risk}</Badge>}</b>
          <small>{option.detail}</small>
          {method && <div className="apply-btn"><button type="button" className={`btn-mini ${recommended ? 'primary' : ''}`}
            disabled={busy} onClick={() => onRepair(issue.column, method, segments?.segment_column)}>
            {recommended ? 'Apply recommendation' : 'Apply repair'}
          </button></div>}
        </div>;
      })}</div>
    </>}
    <div className="rec-box"><b>Recommended repair</b><small>{issue.recommended || 'Review'} · {issue.reason}</small></div>
    {distribution?.histogram?.length > 0 && <>
      <h3>Distribution Snapshot</h3>
      <div className="grid-2">
        <Histogram column={issue.column} distribution={distribution} size="sm" />
        <div className="kpi-row"><Tile label="Skew" value={distribution.skew?.toFixed(2)} />
          <Tile label="Median" value={distribution.median} /><Tile label="Mean" value={distribution.mean} /></div>
      </div>
    </>}
    {segments?.segments?.length > 0 && <><h3>Segment-Level Analysis</h3><SegmentTable analysis={segments} /></>}
  </div>;
}

function Drift({ drift }) {
  if (!drift) return null;
  return <div className={`drift-box ${drift.pass ? 'clean' : ''}`}>
    <b>{drift.pass ? 'No Schema Drift Detected' : `Schema Drift — ${drift.severity}`}</b>
    <small>Added {drift.added?.join(', ') || 'none'} · Removed {drift.removed?.join(', ') || 'none'} · Type changes {
      drift.type_changes?.map(change => `${change.column} (${change.old} → ${change.new})`).join(', ') || 'none'
    }</small>
  </div>;
}

export function Inspection({ datasets, selected, onSelect, detail, error, onRepair, repairStatus, busy }) {
  return <section id="inspect" className="section">
    <Card title="🔍 Dataset Inspection & Intelligent Repair" action={<select aria-label="Dataset to inspect"
      value={selected} onChange={event => onSelect(event.target.value)}>
      <option value="">Select a dataset to inspect</option>
      {selected && !datasets.some(dataset => dataset.dataset_id === selected) && <option value={selected}>{selected}</option>}
      {datasets.map(dataset => <option key={dataset.dataset_id} value={dataset.dataset_id}>
        {dataset.dataset_id} ({(dataset.rows || 0).toLocaleString()} rows, {percent(dataset.quality_score, 0)})
      </option>)}
    </select>}>
      {repairStatus && <div role="status" className={`status-line ${repairStatus.tone}`}>{repairStatus.text}</div>}
      {!selected ? <Empty>Select a dataset to view its profile and repair recommendations.</Empty> :
        error ? <div role="alert" className="empty error-text">{error}</div> :
          detail ? <Detail key={selected} id={selected} data={detail} onRepair={onRepair} busy={busy} /> :
            <Empty>Loading inspection for {selected}…</Empty>}
    </Card>
  </section>;
}

function Detail({ id, data, onRepair, busy }) {
  const [tab, setTab] = useState('features');
  const [column, setColumn] = useState('');
  const result = data.profile || {};
  const profile = result.profile || {};
  const safety = safetyFor(result);
  const issues = safety.issues || [];
  const rules = result.rules || [];
  const columns = result.schema?.columns || [];
  const profiles = profile.column_profiles || {};
  const numeric = columns.filter(item => profiles[item.column]?.histogram?.length || issues.some(
    issue => issue.column === item.column && issue.distribution?.histogram?.length));
  const segmented = issues.filter(issue => issue.segment_analysis?.segments?.length);
  const issueColumn = issues.find(issue => issue.distribution?.histogram?.length)?.column;
  const currentColumn = numeric.some(item => item.column === column)
    ? column : numeric.find(item => item.column === issueColumn)?.column ?? numeric[0]?.column;
  const distribution = profiles[currentColumn]?.histogram?.length ? profiles[currentColumn] :
    issues.find(issue => issue.column === currentColumn)?.distribution;
  const tabs = [
    ['features', 'Feature Intelligence'],
    ...(numeric.length ? [['distribution', 'Distribution']] : []),
    ...(segmented.length ? [['segments', 'Segment Analysis']] : []),
    ['lineage', 'Lineage'],
  ];
  const active = tabs.some(([key]) => key === tab) ? tab : 'features';
  const tone = safety.safe_for_feature_retrieval ? 'safe' : 'blocked';
  return <>
    <div className={`decision-box ${tone}`}><h3>ML Feature Retrieval — {safety.decision}</h3>
      <Badge tone={tone}>{safety.safe_for_feature_retrieval ? 'SAFE FOR ML' : 'BLOCKED PENDING REPAIR'}</Badge>
    </div>
    <div className="kpi-row">
      <Tile label="Dataset" value={id} /><Tile label="Quality Score" value={percent(profile.quality_score)} />
      <Tile label="Issues" value={safety.issue_count ?? rules.length} />
      <Tile label="Rows Affected" value={percent(safety.profiling?.rows_affected_percent ?? 0)} />
    </div>
    <div className="tab-bar" aria-label="Inspection views">
      {tabs.map(([key, label]) => <button key={key} aria-pressed={key === active}
        className={key === active ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}
    </div>
    {active === 'features' && <>
      <h3>Column Profiles</h3>
      <div className="table-scroll"><table className="prof-table">
        <thead><tr>{['Column', 'Inferred Type', 'Dtype', 'Missing', 'Unique', 'Sample Values'].map(label => <th key={label}>{label}</th>)}</tr></thead>
        <tbody>{columns.map(item => {
          const name = item.column;
          const cp = profiles[name] || {};
          return <tr key={name}>
            <td>{numeric.includes(item) ? <button className="btn-mini" onClick={() => { setColumn(name); setTab('distribution'); }}>{name}</button> : name}</td>
            <td>{cp.inferred_type || item.semantic_type || 'unknown'}</td><td>{cp.dtype || 'unknown'}</td>
            <td><Badge tone={missingTone(cp.missing_percent)}>{percent(cp.missing_percent ?? 0)}</Badge> ({cp.missing_count || 0})</td>
            <td>{cp.unique_count ?? '—'}</td><td>{cp.sample_values?.join(', ') || '—'}</td>
          </tr>;
        })}</tbody>
      </table></div>
      <Drift drift={data.drift} />
      <h3>What Needs Attention</h3>
      {issues.length ? issues.map((issue, index) => <Issue key={index} issue={issue} busy={busy} onRepair={onRepair} />) :
        <Empty>No blocking quality issues detected.</Empty>}
      {rules.length > 0 && <><h3>Quality Rules Triggered</h3>{rules.map((rule, index) => <div className="alert-item" key={index}>
        <Badge tone={severityTone(rule.severity)}>{rule.severity}</Badge>
        <div className="body"><strong>{rule.rule_id}</strong><small>{rule.recommendation}<br />
          Observed {String(rule.observed ?? '—')} · Threshold {String(rule.threshold ?? '—')}</small></div>
      </div>)}</>}
    </>}
    {active === 'distribution' && distribution && <>
      <label>Distribution column <select value={currentColumn} onChange={event => setColumn(event.target.value)}>
        {numeric.map(item => <option key={item.column}>{item.column}</option>)}
      </select></label>
      <Distribution column={currentColumn} data={distribution} />
    </>}
    {active === 'segments' && segmented.map((issue, index) => <div key={index}><h3>{issue.column}</h3><SegmentCharts issue={issue} /></div>)}
    {active === 'lineage' && <div className="kpi-row">
      <Tile label="Source path" value={data.lineage?.source} />
      <Tile label="Lineage status" value={data.lineage?.lineage?.status || 'available'} />
      <Tile label="Registered" value={data.registration?.registered_at} />
      <Tile label="Rows" value={profile.rows?.toLocaleString()} />
      {data.registration?.repaired_from && <Tile label="Repaired from" value={data.registration.repaired_from} />}
    </div>}
  </>;
}
