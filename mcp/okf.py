from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

SUPPORT_FILES = {"index.md", "log.md"}
RECOMMENDED_KEYS = ("title", "description", "timestamp")
_FRONTMATTER_DELIM = "---"
_CONCEPT_SEGMENT_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")
_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)")

SEVEN_D_STAGES: tuple[dict[str, Any], ...] = (
    {
        "key": "discover",
        "name": "Discover",
        "order": 1,
        "description": "Problem and value discovery before product and technical design.",
    },
    {
        "key": "design",
        "name": "Design",
        "order": 2,
        "description": "Product, architecture, constraints, scenarios, and readiness design.",
    },
    {
        "key": "develop",
        "name": "Develop",
        "order": 3,
        "description": "Implementation and initial quality verification.",
    },
    {
        "key": "deploy",
        "name": "Deploy",
        "order": 4,
        "description": "Safe deployment to preview or another limited release contour.",
    },
    {
        "key": "day-to-day",
        "name": "Day-to-day",
        "order": 5,
        "description": "Real usage, feedback collection, and improvement planning.",
    },
    {
        "key": "defend",
        "name": "Defend",
        "order": 6,
        "description": "Production-grade security, reliability, support, and GA readiness.",
    },
    {
        "key": "decommission",
        "name": "Decommission",
        "order": 7,
        "description": "Managed shutdown, migration, and final completion confirmation.",
    },
)

SEVEN_D_ARTIFACT_TYPE_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "type": "Product Brief",
        "stage": "discover",
        "responsible": ["PM"],
        "accountable": "PM",
        "consulted": ["Support / GTM", "Tech Lead"],
        "informed": ["Sponsor"],
    },
    {
        "type": "Go / No-Go to Design",
        "stage": "discover",
        "responsible": ["PM"],
        "accountable": "Sponsor",
        "consulted": ["Tech Lead", "Security", "SRE"],
        "informed": ["Support / GTM"],
    },
    {
        "type": "PRD",
        "stage": "design",
        "responsible": ["PM"],
        "accountable": "PM",
        "consulted": ["Tech Lead", "QA", "Support / GTM"],
        "informed": ["Sponsor"],
    },
    {
        "type": "Architecture & NFR",
        "stage": "design",
        "responsible": ["Tech Lead / Architect"],
        "accountable": "Tech Lead / Architect",
        "consulted": ["SRE", "Security", "QA"],
        "informed": ["PM"],
    },
    {
        "type": "Release Candidate",
        "stage": "develop",
        "responsible": ["Tech Lead / Engineering"],
        "accountable": "Tech Lead",
        "consulted": ["QA", "Security", "SRE"],
        "informed": ["PM"],
    },
    {
        "type": "Test Report",
        "stage": "develop",
        "responsible": ["QA"],
        "accountable": "QA",
        "consulted": ["Tech Lead", "PM"],
        "informed": ["SRE"],
    },
    {
        "type": "Deployment & Rollback Plan",
        "stage": "deploy",
        "responsible": ["SRE"],
        "accountable": "SRE",
        "consulted": ["Tech Lead", "QA", "Security"],
        "informed": ["PM"],
    },
    {
        "type": "Preview Launch Package",
        "stage": "deploy",
        "responsible": ["PM"],
        "accountable": "PM",
        "consulted": ["QA", "Support / GTM", "SRE"],
        "informed": ["Sponsor"],
    },
    {
        "type": "Usage & Feedback Report",
        "stage": "day-to-day",
        "responsible": ["PM", "Support / GTM"],
        "accountable": "PM",
        "consulted": ["SRE", "QA", "Tech Lead"],
        "informed": ["Sponsor"],
    },
    {
        "type": "Improvement Backlog",
        "stage": "day-to-day",
        "responsible": ["PM"],
        "accountable": "PM",
        "consulted": ["Tech Lead", "QA", "Support / GTM"],
        "informed": ["Sponsor"],
    },
    {
        "type": "GA Readiness Checklist",
        "stage": "defend",
        "responsible": ["PM"],
        "accountable": "PM",
        "consulted": ["Tech Lead", "SRE", "QA", "Security", "Support / GTM"],
        "informed": ["Sponsor"],
    },
    {
        "type": "Security & Reliability Approval",
        "stage": "defend",
        "responsible": ["Security", "SRE"],
        "accountable": "Security / SRE",
        "consulted": ["Tech Lead", "QA"],
        "informed": ["PM", "Sponsor"],
    },
    {
        "type": "Decommission / Migration Plan",
        "stage": "decommission",
        "responsible": ["PM", "Tech Lead", "SRE"],
        "accountable": "PM",
        "consulted": ["Security", "Support / GTM"],
        "informed": ["Sponsor"],
    },
    {
        "type": "Final Shutdown Report",
        "stage": "decommission",
        "responsible": ["PM", "SRE"],
        "accountable": "PM",
        "consulted": ["Tech Lead", "Security"],
        "informed": ["Sponsor"],
    },
)

_SEVEN_D_STAGE_BY_KEY = {stage["key"]: stage for stage in SEVEN_D_STAGES}
_SEVEN_D_TYPE_BY_NAME = {item["type"].casefold(): item for item in SEVEN_D_ARTIFACT_TYPE_REGISTRY}
_SEVEN_D_FRONTMATTER_KEYS = {
    "process",
    "stage",
    "stage_order",
    "artifact_key",
    "artifact_order",
    "gate_decision",
    "raci",
}


class OKFError(ValueError):
    """Raised when an OKF operation cannot be completed."""


@dataclass
class OKFDocument:
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @classmethod
    def parse(cls, text: str) -> "OKFDocument":
        lines = text.splitlines()
        if not lines or lines[0].strip() != _FRONTMATTER_DELIM:
            return cls(frontmatter={}, body=text)

        end_idx: int | None = None
        for i, line in enumerate(lines[1:], start=1):
            if line.strip() == _FRONTMATTER_DELIM:
                end_idx = i
                break
        if end_idx is None:
            raise OKFError("Unterminated YAML frontmatter block")

        fm_text = "\n".join(lines[1:end_idx])
        try:
            fm = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError as exc:
            raise OKFError(f"Invalid YAML in frontmatter: {exc}") from exc
        if not isinstance(fm, dict):
            raise OKFError("Frontmatter must be a YAML mapping")

        body = "\n".join(lines[end_idx + 1 :])
        if body.startswith("\n"):
            body = body[1:]
        return cls(frontmatter=dict(fm), body=body)

    def serialize(self) -> str:
        fm_text = yaml.safe_dump(
            self.frontmatter,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).rstrip()
        body = self.body if self.body.endswith("\n") else self.body + "\n"
        return f"{_FRONTMATTER_DELIM}\n{fm_text}\n{_FRONTMATTER_DELIM}\n\n{body}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_link(raw: str) -> str:
    target = raw.strip().split()[0]
    target = target.split("#", 1)[0]
    target = target.split("?", 1)[0]
    return target


def _is_external_link(target: str) -> bool:
    lowered = target.lower()
    return (
        not target
        or lowered.startswith(("http://", "https://", "mailto:", "tel:", "urn:"))
        or target.startswith("#")
    )


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except TypeError:
        if isinstance(value, (datetime,)):
            return value.isoformat()
        if isinstance(value, Path):
            return value.as_posix()
        return str(value)


def _safe_frontmatter(frontmatter: dict[str, Any]) -> dict[str, Any]:
    return {str(k): _jsonable(v) for k, v in frontmatter.items()}


def _seven_d_mapping_for_type(type_name: str) -> dict[str, Any] | None:
    item = _SEVEN_D_TYPE_BY_NAME.get(type_name.strip().casefold())
    if not item:
        return None
    mapping = {str(key): _jsonable(value) for key, value in item.items()}
    stage = _SEVEN_D_STAGE_BY_KEY.get(str(item["stage"]))
    if stage:
        mapping["stage_name"] = stage["name"]
        mapping["stage_order"] = stage["order"]
    return mapping


def _seven_d_stage_key(stage: str) -> str:
    value = stage.strip().casefold()
    for item in SEVEN_D_STAGES:
        if value in {str(item["key"]).casefold(), str(item["name"]).casefold()}:
            return str(item["key"])
    raise OKFError(f"Unknown 7D stage: {stage}")


def _snippet(text: str, limit: int = 280) -> str:
    compact = " ".join(part.strip() for part in text.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit].rstrip() + "…"


def _title_from_filename(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()


def _dir_title(path: Path, bundle: Path) -> str:
    if path == bundle:
        return "OKF Bundle"
    return path.name.replace("-", " ").replace("_", " ").title()


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9а-яё]+", "-", value, flags=re.IGNORECASE)
    value = value.strip("-")
    return value or "document"


def _first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or fallback
    return fallback


def _iter_source_docs(source: Path) -> Iterable[Path]:
    for path in sorted(source.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(source).parts):
            continue
        yield path


def _render_graph_html(graph: dict[str, Any]) -> str:
    """Render a self-contained HTML report for an OKF graph."""

    nodes = graph.get("nodes") or []
    edges = graph.get("edges") or []
    type_counts: dict[str, int] = {}
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("type") or "Concept")
        type_counts[node_type] = type_counts.get(node_type, 0) + 1

    top_types = sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))[:12]
    type_badges = "\n".join(
        f'<span class="badge"><b>{html.escape(name)}</b> {count}</span>'
        for name, count in top_types
    )
    if not type_badges:
        type_badges = '<span class="muted">No node types found.</span>'

    graph_json = json.dumps(graph, ensure_ascii=False).replace("</", "<\\/")
    graph_json_literal = json.dumps(graph_json, ensure_ascii=False)

    bundle = html.escape(str(graph.get("bundle") or ""))
    node_count = html.escape(str(graph.get("node_count", len(nodes))))
    edge_count = html.escape(str(graph.get("edge_count", len(edges))))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OKF Graph Report</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #0f172a;
      --panel: #111827;
      --panel-2: #1f2937;
      --text: #e5e7eb;
      --muted: #9ca3af;
      --line: #374151;
      --accent: #38bdf8;
      --accent-2: #a78bfa;
      --danger: #fb7185;
      --ok: #34d399;
    }}
    @media (prefers-color-scheme: light) {{
      :root {{ --bg: #f8fafc; --panel: #ffffff; --panel-2: #f1f5f9; --text: #0f172a; --muted: #64748b; --line: #cbd5e1; }}
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); }}
    header {{ padding: 24px; border-bottom: 1px solid var(--line); background: var(--panel); }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .muted {{ color: var(--muted); }}
    .layout {{ display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 16px; padding: 16px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 14px; overflow: hidden; }}
    .panel h2 {{ margin: 0; padding: 14px 16px; font-size: 16px; border-bottom: 1px solid var(--line); background: var(--panel-2); }}
    .stats {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }}
    .stat, .badge {{ display: inline-flex; gap: 8px; align-items: baseline; padding: 8px 10px; border-radius: 999px; background: var(--panel-2); border: 1px solid var(--line); }}
    .stat b {{ font-size: 18px; }}
    .toolbar {{ display: flex; gap: 10px; padding: 12px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }}
    input, select {{ color: var(--text); background: var(--panel-2); border: 1px solid var(--line); border-radius: 10px; padding: 9px 10px; min-width: 160px; }}
    input {{ flex: 1; }}
    svg {{ display: block; width: 100%; height: 620px; background: radial-gradient(circle at 50% 35%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 45%); }}
    .edge {{ stroke: var(--line); stroke-opacity: .72; }}
    .edge.active {{ stroke: var(--accent); stroke-opacity: 1; stroke-width: 2.5; }}
    .node circle {{ stroke: rgba(255,255,255,.55); stroke-width: 1.5; cursor: pointer; }}
    .node text {{ pointer-events: none; fill: currentColor; font-size: 11px; paint-order: stroke; stroke: var(--bg); stroke-width: 3px; stroke-linejoin: round; }}
    .node.dim, .edge.dim {{ opacity: .12; }}
    .node.selected circle {{ stroke: var(--danger); stroke-width: 3; }}
    .side {{ padding: 14px; }}
    .side dl {{ margin: 0; display: grid; gap: 10px; }}
    .side dt {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
    .side dd {{ margin: 0; overflow-wrap: anywhere; }}
    .table-wrap {{ max-height: 360px; overflow: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ position: sticky; top: 0; background: var(--panel-2); }}
    tr {{ cursor: pointer; }}
    tr:hover {{ background: var(--panel-2); }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 12px; }}
    @media (max-width: 980px) {{ .layout {{ grid-template-columns: 1fr; }} svg {{ height: 520px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>OKF Graph Report</h1>
    <div class="muted">Bundle: <code>{bundle}</code></div>
    <div class="stats">
      <span class="stat"><b>{node_count}</b> nodes</span>
      <span class="stat"><b>{edge_count}</b> edges</span>
      <span class="stat"><b id="visible-count">{node_count}</b> visible</span>
    </div>
  </header>

  <main class="layout">
    <section class="panel">
      <div class="toolbar">
        <input id="search" type="search" placeholder="Filter by id, title, type, description, tags…" aria-label="Filter nodes">
        <select id="type-filter" aria-label="Filter by type"><option value="">All types</option></select>
      </div>
      <svg id="graph" role="img" aria-label="OKF concept graph"></svg>
    </section>

    <aside class="panel">
      <h2>Selected concept</h2>
      <div id="details" class="side muted">Select a node in the graph or table.</div>
    </aside>

    <section class="panel">
      <h2>Concept types</h2>
      <div class="chips">{type_badges}</div>
    </section>

    <section class="panel">
      <h2>Nodes</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Title</th><th>Type</th><th>Links</th></tr></thead>
          <tbody id="node-table"></tbody>
        </table>
      </div>
    </section>
  </main>

  <script>
    const graph = JSON.parse({graph_json_literal});
    const nodes = (graph.nodes || []).map((node, index) => ({{ ...node, index }}));
    const edges = graph.edges || [];
    const byId = new Map(nodes.map(node => [node.id, node]));
    const outgoing = new Map();
    const incoming = new Map();
    for (const edge of edges) {{
      if (!outgoing.has(edge.source)) outgoing.set(edge.source, []);
      if (!incoming.has(edge.target)) incoming.set(edge.target, []);
      outgoing.get(edge.source).push(edge);
      incoming.get(edge.target).push(edge);
    }}

    const palette = ['#38bdf8', '#a78bfa', '#34d399', '#fbbf24', '#fb7185', '#60a5fa', '#f472b6', '#2dd4bf', '#c084fc', '#f97316'];
    const types = [...new Set(nodes.map(node => node.type || 'Concept'))].sort();
    const colorByType = new Map(types.map((type, index) => [type, palette[index % palette.length]]));

    const svg = document.getElementById('graph');
    const search = document.getElementById('search');
    const typeFilter = document.getElementById('type-filter');
    const table = document.getElementById('node-table');
    const details = document.getElementById('details');
    const visibleCount = document.getElementById('visible-count');
    let selectedId = null;

    for (const type of types) {{
      const option = document.createElement('option');
      option.value = type;
      option.textContent = type;
      typeFilter.appendChild(option);
    }}

    function textOf(node) {{
      return [node.id, node.path, node.type, node.title, node.description, (node.tags || []).join(' ')].join(' ').toLowerCase();
    }}

    function visibleNodes() {{
      const q = search.value.trim().toLowerCase();
      const type = typeFilter.value;
      return nodes.filter(node => (!type || (node.type || 'Concept') === type) && (!q || textOf(node).includes(q)));
    }}

    function layout(list) {{
      const width = svg.clientWidth || 900;
      const height = svg.clientHeight || 620;
      const cx = width / 2;
      const cy = height / 2;
      const radius = Math.max(80, Math.min(width, height) * 0.38);
      const visibleSet = new Set(list.map(node => node.id));
      list.forEach((node, i) => {{
        const angle = (Math.PI * 2 * i) / Math.max(1, list.length);
        node.x = cx + Math.cos(angle) * radius * (0.65 + (i % 5) * 0.07);
        node.y = cy + Math.sin(angle) * radius * (0.65 + (i % 7) * 0.05);
      }});
      const visibleEdges = edges.filter(edge => visibleSet.has(edge.source) && visibleSet.has(edge.target));
      for (let step = 0; step < 180; step++) {{
        for (let i = 0; i < list.length; i++) {{
          for (let j = i + 1; j < list.length; j++) {{
            const a = list[i];
            const b = list[j];
            let dx = a.x - b.x;
            let dy = a.y - b.y;
            let d2 = Math.max(36, dx * dx + dy * dy);
            const force = Math.min(4, 900 / d2);
            const d = Math.sqrt(d2);
            dx /= d; dy /= d;
            a.x += dx * force; a.y += dy * force;
            b.x -= dx * force; b.y -= dy * force;
          }}
        }}
        for (const edge of visibleEdges) {{
          const a = byId.get(edge.source);
          const b = byId.get(edge.target);
          if (!a || !b) continue;
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          a.x += dx * 0.01; a.y += dy * 0.01;
          b.x -= dx * 0.01; b.y -= dy * 0.01;
        }}
        for (const node of list) {{
          node.x += (cx - node.x) * 0.006;
          node.y += (cy - node.y) * 0.006;
          node.x = Math.max(30, Math.min(width - 30, node.x));
          node.y = Math.max(30, Math.min(height - 30, node.y));
        }}
      }}
      return visibleEdges;
    }}

    function escapeText(value) {{ return value == null ? '' : String(value); }}

    function selectNode(id) {{
      selectedId = id;
      const node = byId.get(id);
      if (!node) return;
      const out = outgoing.get(id) || [];
      const inc = incoming.get(id) || [];
      const tags = Array.isArray(node.tags) ? node.tags.join(', ') : escapeText(node.tags);
      details.classList.remove('muted');
      details.innerHTML = '';
      const dl = document.createElement('dl');
      const rows = [
        ['Title', node.title || node.id],
        ['ID', node.id],
        ['Path', node.path || ''],
        ['Type', node.type || 'Concept'],
        ['Description', node.description || ''],
        ['Tags', tags],
        ['Outgoing links', out.map(edge => edge.target).join('\n') || '—'],
        ['Incoming links', inc.map(edge => edge.source).join('\n') || '—'],
      ];
      for (const [key, value] of rows) {{
        const dt = document.createElement('dt'); dt.textContent = key;
        const dd = document.createElement('dd'); dd.textContent = value;
        dl.append(dt, dd);
      }}
      details.appendChild(dl);
      render();
    }}

    function renderTable(list) {{
      table.innerHTML = '';
      for (const node of list) {{
        const tr = document.createElement('tr');
        tr.innerHTML = '<td></td><td></td><td></td>';
        tr.children[0].textContent = node.title || node.id;
        tr.children[1].textContent = node.type || 'Concept';
        tr.children[2].textContent = `${{(outgoing.get(node.id) || []).length}} out / ${{(incoming.get(node.id) || []).length}} in`;
        tr.addEventListener('click', () => selectNode(node.id));
        table.appendChild(tr);
      }}
    }}

    function render() {{
      const list = visibleNodes();
      const visibleSet = new Set(list.map(node => node.id));
      const visibleEdges = layout(list);
      visibleCount.textContent = String(list.length);
      svg.innerHTML = '';
      const edgeLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      const nodeLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      svg.append(edgeLayer, nodeLayer);

      for (const edge of visibleEdges) {{
        const source = byId.get(edge.source);
        const target = byId.get(edge.target);
        if (!source || !target) continue;
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', source.x); line.setAttribute('y1', source.y);
        line.setAttribute('x2', target.x); line.setAttribute('y2', target.y);
        const active = selectedId && (edge.source === selectedId || edge.target === selectedId);
        line.setAttribute('class', 'edge' + (active ? ' active' : selectedId ? ' dim' : ''));
        edgeLayer.appendChild(line);
      }}

      for (const node of list) {{
        const degree = (outgoing.get(node.id) || []).length + (incoming.get(node.id) || []).length;
        const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        const related = !selectedId || selectedId === node.id || visibleEdges.some(edge =>
          (edge.source === selectedId && edge.target === node.id) || (edge.target === selectedId && edge.source === node.id)
        );
        group.setAttribute('class', 'node' + (node.id === selectedId ? ' selected' : related ? '' : ' dim'));
        group.setAttribute('transform', `translate(${{node.x}},${{node.y}})`);
        group.addEventListener('click', () => selectNode(node.id));
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('r', Math.min(22, 8 + Math.sqrt(degree + 1) * 4));
        circle.setAttribute('fill', colorByType.get(node.type || 'Concept') || '#38bdf8');
        const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
        title.textContent = `${{node.title || node.id}}\n${{node.id}}`;
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('dy', 32);
        text.textContent = (node.title || node.id).slice(0, 28);
        group.append(title, circle, text);
        nodeLayer.appendChild(group);
      }}
      renderTable(list);
    }}

    search.addEventListener('input', render);
    typeFilter.addEventListener('change', render);
    svg.addEventListener('click', event => {{ if (event.target === svg) {{ selectedId = null; details.textContent = 'Select a node in the graph or table.'; details.classList.add('muted'); render(); }} }});
    window.addEventListener('resize', render);
    render();
  </script>
</body>
</html>
"""


class OKFBundle:
    """Filesystem-backed OKF bundle reader/writer."""

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def ensure_exists(self) -> None:
        if not self.root.exists() or not self.root.is_dir():
            raise OKFError(f"Bundle directory does not exist: {self.root}")

    def concept_id_to_path(self, concept_id: str) -> Path:
        parts = [part for part in concept_id.strip("/").split("/") if part]
        if not parts:
            raise OKFError("concept_id must not be empty")
        for part in parts:
            if not _CONCEPT_SEGMENT_RE.fullmatch(part):
                raise OKFError(f"Invalid concept_id segment: {part!r}")
        if parts[-1].endswith(".md"):
            parts[-1] = parts[-1][:-3]
        if f"{parts[-1]}.md" in SUPPORT_FILES:
            raise OKFError("index.md and log.md are support files, not concepts")
        *dirs, name = parts
        path = self.root.joinpath(*dirs, f"{name}.md").resolve()
        self._assert_inside(path)
        return path

    def support_path(self, relative_path: str) -> Path:
        rel = relative_path.strip().lstrip("/") or "index.md"
        path = (self.root / rel).resolve()
        self._assert_inside(path)
        if path.suffix != ".md" and path.name != "graph.json":
            raise OKFError("Only Markdown support files and graph.json can be read")
        return path

    def path_to_concept_id(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).with_suffix("").as_posix()

    def _assert_inside(self, path: Path) -> None:
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise OKFError(f"Path escapes bundle root: {path}") from exc

    def iter_markdown(self, *, include_support: bool = True) -> Iterable[Path]:
        self.ensure_exists()
        for path in sorted(self.root.rglob("*.md")):
            rel_parts = path.relative_to(self.root).parts
            if any(part.startswith(".") for part in rel_parts):
                continue
            if not include_support and path.name in SUPPORT_FILES:
                continue
            yield path

    def iter_concepts(self) -> Iterable[Path]:
        yield from self.iter_markdown(include_support=False)

    def read_document(self, concept_id: str) -> OKFDocument:
        path = self.concept_id_to_path(concept_id)
        if not path.exists():
            raise OKFError(f"Concept does not exist: {concept_id}")
        return OKFDocument.parse(path.read_text(encoding="utf-8"))

    def read_concept(self, concept_id: str, *, include_body: bool = True) -> dict[str, Any]:
        path = self.concept_id_to_path(concept_id)
        if not path.exists():
            raise OKFError(f"Concept does not exist: {concept_id}")
        doc = OKFDocument.parse(path.read_text(encoding="utf-8"))
        result: dict[str, Any] = {
            "id": self.path_to_concept_id(path),
            "path": path.relative_to(self.root).as_posix(),
            "frontmatter": _safe_frontmatter(doc.frontmatter),
            "title": str(doc.frontmatter.get("title") or path.stem),
            "type": str(doc.frontmatter.get("type") or ""),
            "description": str(doc.frontmatter.get("description") or ""),
        }
        if include_body:
            result["body"] = doc.body
        return result

    def read_raw(self, concept_id: str) -> str:
        path = self.concept_id_to_path(concept_id)
        if not path.exists():
            raise OKFError(f"Concept does not exist: {concept_id}")
        return path.read_text(encoding="utf-8")

    def read_support_file(self, relative_path: str = "index.md") -> dict[str, Any]:
        path = self.support_path(relative_path)
        if not path.exists():
            raise OKFError(f"Support file does not exist: {relative_path}")
        return {
            "path": path.relative_to(self.root).as_posix(),
            "text": path.read_text(encoding="utf-8"),
        }

    def list_concepts(
        self,
        *,
        type_filter: str | None = None,
        tag: str | None = None,
        query: str | None = None,
        include_snippet: bool = False,
    ) -> list[dict[str, Any]]:
        q = query.lower() if query else None
        type_q = type_filter.lower() if type_filter else None
        tag_q = tag.lower() if tag else None
        out: list[dict[str, Any]] = []

        for path in self.iter_concepts():
            try:
                doc = OKFDocument.parse(path.read_text(encoding="utf-8"))
            except OKFError:
                continue
            fm = doc.frontmatter
            tags = fm.get("tags") or []
            if isinstance(tags, str):
                tags = [tags]
            tags = [str(t) for t in tags]
            typ = str(fm.get("type") or "")
            title = str(fm.get("title") or path.stem)
            desc = str(fm.get("description") or "")
            cid = self.path_to_concept_id(path)

            if type_q and typ.lower() != type_q:
                continue
            if tag_q and tag_q not in {t.lower() for t in tags}:
                continue
            haystack = "\n".join([cid, typ, title, desc, " ".join(tags), doc.body]).lower()
            if q and q not in haystack:
                continue

            item: dict[str, Any] = {
                "id": cid,
                "path": path.relative_to(self.root).as_posix(),
                "type": typ,
                "title": title,
                "description": desc,
                "tags": tags,
                "resource": fm.get("resource", ""),
            }
            if include_snippet:
                item["snippet"] = _snippet(doc.body)
            out.append(item)
        return out

    def search_concepts(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        if not query.strip():
            raise OKFError("query must not be empty")
        q = query.lower()
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in self.list_concepts(include_snippet=True):
            doc = self.read_document(item["id"])
            score = 0
            for field, weight in (
                (item["id"], 6),
                (item.get("title", ""), 8),
                (item.get("description", ""), 5),
                (item.get("type", ""), 3),
                (" ".join(item.get("tags") or []), 4),
                (doc.body, 1),
            ):
                score += str(field).lower().count(q) * weight
            if score:
                item["score"] = score
                scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
        return [item for _, item in scored[: max(1, int(limit))]]

    def seven_d_registry(self) -> dict[str, Any]:
        """Return the static 7D stage and artifact-type mapping registry."""
        return {
            "stages": [_safe_frontmatter(dict(item)) for item in SEVEN_D_STAGES],
            "artifact_types": [_safe_frontmatter(dict(item)) for item in SEVEN_D_ARTIFACT_TYPE_REGISTRY],
        }

    def seven_d_mapping_for_type(self, type_name: str) -> dict[str, Any] | None:
        """Return the 7D mapping for an OKF concept type, if one exists."""
        return _seven_d_mapping_for_type(type_name)

    def list_7d_artifact_concepts(self, stage: str | None = None) -> list[dict[str, Any]]:
        """List concepts whose `type` is registered as a 7D artifact type."""
        stage_key = _seven_d_stage_key(stage) if stage else None
        out: list[dict[str, Any]] = []
        for concept in self.list_concepts():
            mapping = _seven_d_mapping_for_type(str(concept.get("type") or ""))
            if not mapping:
                continue
            if stage_key and mapping.get("stage") != stage_key:
                continue
            item = dict(concept)
            item["seven_d"] = mapping
            out.append(item)
        out.sort(
            key=lambda item: (
                int(item["seven_d"].get("stage_order") or 0),
                str(item.get("type") or ""),
                str(item.get("id") or ""),
            )
        )
        return out

    def seven_d_feature_status(self, concept_id: str) -> dict[str, Any]:
        """Derive a concept's 7D progress from its own or linked artifact types."""
        concept = self.read_concept(concept_id, include_body=False)
        graph = self.build_graph()
        nodes = {str(node.get("id")): node for node in graph.get("nodes", []) if isinstance(node, dict)}
        if concept["id"] not in nodes:
            raise OKFError(f"Concept does not exist in graph: {concept_id}")

        related: dict[str, set[str]] = {concept["id"]: {"self"}}
        for edge in graph.get("edges", []):
            if not isinstance(edge, dict):
                continue
            source = str(edge.get("source") or "")
            target = str(edge.get("target") or "")
            if source == concept["id"] and target:
                related.setdefault(target, set()).add("outgoing")
            if target == concept["id"] and source:
                related.setdefault(source, set()).add("incoming")

        artifacts: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []
        for related_id, directions in related.items():
            node = nodes.get(related_id)
            if not node:
                continue
            node_type = str(node.get("type") or "")
            mapping = _seven_d_mapping_for_type(node_type)
            if not mapping:
                if related_id != concept["id"]:
                    gaps.append(
                        {
                            "id": related_id,
                            "path": node.get("path", ""),
                            "type": node_type,
                            "title": node.get("title", related_id),
                            "relationship": sorted(directions),
                            "reason": "Concept type is not registered in the 7D artifact-type registry.",
                        }
                    )
                continue
            artifacts.append(
                {
                    "id": related_id,
                    "path": node.get("path", ""),
                    "type": node_type,
                    "title": node.get("title", related_id),
                    "description": node.get("description", ""),
                    "relationship": sorted(directions),
                    "seven_d": mapping,
                }
            )

        gaps.sort(key=lambda item: (str(item.get("id") or ""), str(item.get("relationship") or "")))
        artifacts.sort(
            key=lambda item: (
                int(item["seven_d"].get("stage_order") or 0),
                str(item.get("type") or ""),
                str(item.get("id") or ""),
            )
        )
        current = artifacts[-1]["seven_d"] if artifacts else None
        return {
            "concept": concept,
            "derived_stage": current,
            "artifact_count": len(artifacts),
            "artifacts": artifacts,
            "gaps": gaps,
            "gap_count": len(gaps),
            "note": (
                "7D stage is derived from the highest-order registered artifact type linked to the concept."
                if artifacts
                else "No linked concepts with registered 7D artifact types were found."
            ),
        }

    def validate_7d(self) -> dict[str, Any]:
        """Validate 7D registry usage without changing the OKF concept format."""
        self.ensure_exists()
        errors: list[str] = []
        warnings: list[str] = []
        mapped_count = 0

        stage_keys = {str(item["key"]) for item in SEVEN_D_STAGES}
        for item in SEVEN_D_ARTIFACT_TYPE_REGISTRY:
            if item["stage"] not in stage_keys:
                errors.append(f"7D registry type `{item['type']}` references unknown stage `{item['stage']}`")
            accountable = str(item.get("accountable") or "").strip()
            if not accountable:
                errors.append(f"7D registry type `{item['type']}` has no accountable role")

        for path in self.iter_concepts():
            rel = path.relative_to(self.root).as_posix()
            try:
                doc = OKFDocument.parse(path.read_text(encoding="utf-8"))
            except OKFError as exc:
                errors.append(f"{rel}: {exc}")
                continue
            typ = str(doc.frontmatter.get("type") or "")
            if _seven_d_mapping_for_type(typ):
                mapped_count += 1
            disallowed = sorted(key for key in _SEVEN_D_FRONTMATTER_KEYS if key in doc.frontmatter)
            if disallowed:
                warnings.append(
                    f"{rel}: 7D should be derived from `type`; avoid 7D-specific frontmatter keys: "
                    f"{', '.join(disallowed)}"
                )

        return {
            "bundle": str(self.root),
            "mapped_concept_count": mapped_count,
            "registered_artifact_type_count": len(SEVEN_D_ARTIFACT_TYPE_REGISTRY),
            "stage_count": len(SEVEN_D_STAGES),
            "errors": errors,
            "warnings": warnings,
            "ok": not errors,
        }

    def list_directory(self, directory: str = "") -> dict[str, Any]:
        self.ensure_exists()
        rel = directory.strip().strip("/")
        path = (self.root / rel).resolve() if rel else self.root
        self._assert_inside(path)
        if not path.exists() or not path.is_dir():
            raise OKFError(f"Directory does not exist: {directory}")

        dirs: list[dict[str, str]] = []
        concepts: list[dict[str, Any]] = []
        support_files: list[dict[str, str]] = []

        for child in sorted(path.iterdir()):
            if child.name.startswith("."):
                continue
            child_rel = child.relative_to(self.root).as_posix()
            if child.is_dir():
                dirs.append({"name": child.name, "path": child_rel})
            elif child.suffix == ".md" and child.name in SUPPORT_FILES:
                support_files.append({"name": child.name, "path": child_rel})
            elif child.suffix == ".md":
                try:
                    concepts.append(self.read_concept(self.path_to_concept_id(child), include_body=False))
                except OKFError:
                    concepts.append({"id": self.path_to_concept_id(child), "path": child_rel})

        return {
            "path": path.relative_to(self.root).as_posix() if path != self.root else "",
            "directories": dirs,
            "concepts": concepts,
            "support_files": support_files,
        }

    def write_concept(
        self,
        concept_id: str,
        frontmatter: dict[str, Any],
        body: str,
        *,
        overwrite: bool = True,
        merge_frontmatter: bool = True,
    ) -> dict[str, Any]:
        if not isinstance(frontmatter, dict):
            raise OKFError("frontmatter must be an object")
        if not frontmatter.get("type"):
            raise OKFError("frontmatter.type is required")
        if not isinstance(body, str):
            raise OKFError("body must be a string")

        path = self.concept_id_to_path(concept_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite:
            raise OKFError(f"Concept already exists: {concept_id}")

        fm = dict(frontmatter)
        if path.exists() and merge_frontmatter:
            existing = OKFDocument.parse(path.read_text(encoding="utf-8")).frontmatter
            existing.update(fm)
            fm = existing
        fm.setdefault("timestamp", utc_now_iso())

        doc = OKFDocument(frontmatter=fm, body=body)
        text = doc.serialize()
        path.write_text(text, encoding="utf-8")
        return {
            "id": self.path_to_concept_id(path),
            "path": path.relative_to(self.root).as_posix(),
            "bytes": len(text.encode("utf-8")),
            "frontmatter": _safe_frontmatter(fm),
        }

    def _resolve_link(self, source: Path, target: str) -> Path:
        if target.startswith("/"):
            return (self.root / target.lstrip("/")).resolve()
        return (source.parent / target).resolve()

    def build_graph(self) -> dict[str, Any]:
        self.ensure_exists()
        concept_paths = list(self.iter_concepts())
        id_by_path = {path.resolve(): self.path_to_concept_id(path) for path in concept_paths}
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []

        for path in concept_paths:
            text = path.read_text(encoding="utf-8")
            try:
                doc = OKFDocument.parse(text)
            except OKFError:
                doc = OKFDocument()
            fm = doc.frontmatter
            node = {
                "id": self.path_to_concept_id(path),
                "path": path.relative_to(self.root).as_posix(),
                "type": fm.get("type", ""),
                "title": fm.get("title", path.stem),
                "description": fm.get("description", ""),
                "tags": fm.get("tags", []),
                "resource": fm.get("resource", ""),
            }
            nodes.append(_safe_frontmatter(node))

            for match in _LINK_RE.finditer(text):
                label = match.group(1)
                raw_target = match.group(2)
                target = _normalize_link(raw_target)
                if _is_external_link(target) or not target.endswith(".md"):
                    continue
                resolved = self._resolve_link(path, target)
                target_id = id_by_path.get(resolved)
                if not target_id:
                    continue
                edges.append(
                    {
                        "source": node["id"],
                        "target": target_id,
                        "label": label,
                        "href": raw_target,
                        "line": text.count("\n", 0, match.start()) + 1,
                    }
                )

        return {
            "bundle": str(self.root),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        }

    def write_graph(self, out_path: str | Path = "graph.json") -> dict[str, Any]:
        graph = self.build_graph()
        out = Path(out_path)
        if not out.is_absolute():
            out = self.root / out
        out = out.resolve()
        self._assert_inside(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(graph, ensure_ascii=False) + "\n", encoding="utf-8")
        return {"path": out.relative_to(self.root).as_posix(), **graph}

    def render_graph_html(self, graph: dict[str, Any] | None = None) -> str:
        """Return a self-contained HTML report for the OKF graph."""
        return _render_graph_html(graph or self.build_graph())

    def write_graph_html(
        self,
        out_path: str | Path = "graph.html",
        *,
        graph: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Write a self-contained HTML graph report inside the bundle."""
        graph_data = graph or self.build_graph()
        out = Path(out_path)
        if not out.is_absolute():
            out = self.root / out
        out = out.resolve()
        self._assert_inside(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        html_text = self.render_graph_html(graph_data)
        out.write_text(html_text, encoding="utf-8")
        return {
            "path": out.relative_to(self.root).as_posix(),
            "bytes": len(html_text.encode("utf-8")),
            "node_count": graph_data.get("node_count", 0),
            "edge_count": graph_data.get("edge_count", 0),
        }

    def _render_index(self, directory: Path) -> str:
        lines: list[str] = [f"# {_dir_title(directory, self.root)}", ""]

        dirs = [p for p in sorted(directory.iterdir()) if p.is_dir() and not p.name.startswith(".")]
        if dirs:
            lines.append("## Directories")
            lines.append("")
            for child in dirs:
                lines.append(f"* [{_dir_title(child, self.root)}]({child.name}/index.md)")
            lines.append("")

        grouped: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
        for file in sorted(directory.iterdir()):
            if not (file.is_file() and file.suffix == ".md" and file.name not in SUPPORT_FILES):
                continue
            try:
                fm = OKFDocument.parse(file.read_text(encoding="utf-8")).frontmatter
            except OKFError:
                fm = {}
            grouped.setdefault(str(fm.get("type") or "Concept"), []).append((file, fm))

        for type_name in sorted(grouped):
            lines.append(f"## {type_name}")
            lines.append("")
            for file, fm in sorted(grouped[type_name], key=lambda item: item[0].name):
                title = str(fm.get("title") or _title_from_filename(file))
                description = str(fm.get("description") or "")
                suffix = f" - {description}" if description else ""
                lines.append(f"* [{title}]({file.name}){suffix}")
            lines.append("")

        if len(lines) == 2:
            lines.append("No concepts yet.")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def generate_indexes(self) -> dict[str, Any]:
        """Regenerate index.md files for every directory in the bundle."""
        self.ensure_exists()
        directories = [self.root] + sorted(p for p in self.root.rglob("*") if p.is_dir())
        written: list[str] = []
        for directory in directories:
            if any(part.startswith(".") for part in directory.relative_to(self.root).parts):
                continue
            index_path = directory / "index.md"
            index_path.write_text(self._render_index(directory), encoding="utf-8")
            written.append(index_path.relative_to(self.root).as_posix())
        return {"bundle": str(self.root), "count": len(written), "written": written}

    def export_source_documents(
        self,
        source: str | Path = "system",
        *,
        force: bool = False,
        project_root: str | Path | None = None,
    ) -> dict[str, Any]:
        """Export Markdown source files as Source Document concepts."""
        root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = root / source_path
        source_path = source_path.resolve()
        if not source_path.exists() or not source_path.is_dir():
            raise OKFError(f"Source directory does not exist: {source_path}")

        documents = self.root / "documents"
        documents.mkdir(parents=True, exist_ok=True)
        written: list[str] = []
        skipped: list[str] = []

        for source_file in _iter_source_docs(source_path):
            rel = source_file.relative_to(source_path)
            concept_id = f"documents/{_slugify(rel.with_suffix('').as_posix())}"
            target = self.concept_id_to_path(concept_id)
            if target.exists() and not force:
                skipped.append(target.relative_to(self.root).as_posix())
                continue

            text = source_file.read_text(encoding="utf-8")
            try:
                rel_source = source_file.relative_to(root).as_posix()
            except ValueError:
                rel_source = source_file.as_posix()
            title = _first_heading(text, _title_from_filename(source_file))
            body = (
                f"# Overview\n\n"
                f"This concept represents the canonical source document `{rel_source}`.\n\n"
                f"# Source\n\n"
                f"Canonical source: [{rel_source}](../../../{rel_source})\n\n"
                f"# Extracted body\n\n"
                f"{text.rstrip()}\n"
            )
            self.write_concept(
                concept_id,
                {
                    "type": "Source Document",
                    "title": title,
                    "description": "Canonical source document exported to OKF.",
                    "resource": rel_source,
                    "tags": ["source-document"],
                    "timestamp": utc_now_iso(),
                    "source_path": rel_source,
                    "owner_document": source_file.name,
                },
                body,
                overwrite=True,
                merge_frontmatter=False,
            )
            written.append(target.relative_to(self.root).as_posix())

        return {
            "bundle": str(self.root),
            "source": str(source_path),
            "written_count": len(written),
            "skipped_count": len(skipped),
            "written": written,
            "skipped": skipped,
        }

    def validate(self) -> dict[str, Any]:
        self.ensure_exists()
        errors: list[str] = []
        warnings: list[str] = []
        requirement_ids: dict[str, Path] = {}
        concept_count = 0

        for path in self.iter_markdown(include_support=True):
            rel = path.relative_to(self.root).as_posix()
            text = path.read_text(encoding="utf-8")
            doc: OKFDocument | None = None

            if path.name not in SUPPORT_FILES:
                concept_count += 1
                try:
                    doc = OKFDocument.parse(text)
                except OKFError as exc:
                    errors.append(f"{rel}: {exc}")
                    doc = OKFDocument()
                if "type" not in doc.frontmatter:
                    errors.append(f"{rel}: missing required frontmatter key `type`")
                for key in RECOMMENDED_KEYS:
                    if key not in doc.frontmatter:
                        warnings.append(f"{rel}: missing recommended frontmatter key `{key}`")
                req_id = doc.frontmatter.get("requirement_id")
                if req_id:
                    req_id = str(req_id)
                    if req_id in requirement_ids:
                        errors.append(
                            f"{rel}: duplicate requirement_id `{req_id}` also used by "
                            f"{requirement_ids[req_id].relative_to(self.root).as_posix()}`"
                        )
                    else:
                        requirement_ids[req_id] = path

            for match in _LINK_RE.finditer(text):
                target = _normalize_link(match.group(2))
                if _is_external_link(target) or not target.endswith(".md"):
                    continue
                resolved = self._resolve_link(path, target)
                try:
                    resolved.relative_to(self.root)
                except ValueError:
                    continue
                if not resolved.exists():
                    errors.append(f"{rel}: broken link `{match.group(2)}`")

        return {
            "bundle": str(self.root),
            "concept_count": concept_count,
            "errors": errors,
            "warnings": warnings,
            "ok": not errors,
        }
