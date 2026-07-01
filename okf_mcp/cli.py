from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Callable, Sequence

import typer
from uuid import uuid4

from .okf import OKFBundle, OKFError
from .rag import OKFRagRetriever, OKFRagCorpus, RagConfigError, RagReadinessError, check_rag_readiness, load_settings

DEFAULT_BUNDLE = os.environ.get("OKF_BUNDLE", "okf")


def _load_create_mcp() -> Callable[..., object]:
    from .server import create_mcp

    return create_mcp


def _json_dump(payload: Any, *, pretty: bool = False) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None))


def _relative_display(path_text: str) -> str:
    try:
        return str(Path(path_text).relative_to(Path.cwd()))
    except ValueError:
        return path_text


def _export_bundle_from_out(out: Path) -> Path:
    # Accept both the historical bundle path (`--out okf`) and the multi-app
    # shape (`--out okf/documents`) without changing OKFBundle ownership.
    return out.parent if out.name == "documents" else out


def validate_bundle(bundle: Path) -> int:
    try:
        result = OKFBundle(bundle).validate()
    except OKFError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    for error in result["errors"]:
        print(f"ERROR: {error}", file=sys.stderr)

    print(f"Validated {result['concept_count']} concept file(s) in {_relative_display(result['bundle'])}.")
    if result["errors"]:
        print(
            f"FAILED: {len(result['errors'])} error(s), {len(result['warnings'])} warning(s).",
            file=sys.stderr,
        )
        return 1

    print(f"OK: 0 error(s), {len(result['warnings'])} warning(s).")
    return 0


def generate_indexes(bundle: Path) -> int:
    try:
        result = OKFBundle(bundle).generate_indexes()
    except OKFError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Generated {result['count']} index file(s) under {result['bundle']}")
    return 0


def export_documents(source: Path, out: Path, *, force: bool = False) -> int:
    bundle = _export_bundle_from_out(out)
    try:
        result = OKFBundle(bundle).export_source_documents(source, force=force, project_root=Path.cwd())
    except OKFError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Exported {result['written_count']} document concept(s) to {Path(result['bundle']) / 'documents'}")
    if result["skipped_count"]:
        print(f"Skipped {result['skipped_count']} existing file(s). Use --force to overwrite.")
    return 0


def generate_graph(bundle_path: Path, *, out: str | None = None, html_out: str | None = None, pretty: bool = False) -> int:
    if not bundle_path.exists() or not bundle_path.is_dir():
        print(f"ERROR: bundle directory does not exist: {bundle_path}", file=sys.stderr)
        return 2

    bundle = OKFBundle(bundle_path)
    try:
        graph = bundle.build_graph()
        json_text = json.dumps(graph, ensure_ascii=False, indent=2 if pretty else None)
        if out:
            out_path = bundle.generated_artifact_path(out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json_text + "\n", encoding="utf-8")
            print(
                "Wrote OKF graph JSON: "
                f"{bundle.artifact_display_path(out_path)} ({graph['node_count']} nodes, {graph['edge_count']} edges)"
            )
        elif not html_out:
            print(json_text)

        if html_out:
            html_result = bundle.write_graph_html(html_out, graph=graph)
            print(
                "Wrote OKF graph HTML: "
                f"{html_result['path']} ({graph['node_count']} nodes, {graph['edge_count']} edges)"
            )
    except (OSError, OKFError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    return 0


def rag_inspect(*, env: str | None = None, pretty: bool = False) -> int:
    try:
        settings = load_settings(Path(env) if env else None)
        inventory = OKFRagCorpus(settings.bundle_dir).inspect(str(uuid4()))
    except RagConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    payload = {
        "env_file": str(settings.env_file),
        "artifacts_dir": str(settings.artifacts_dir),
        **inventory.to_dict(),
    }
    _json_dump(payload, pretty=pretty)
    return 0


def rag_refresh(*, env: str | None = None, mode: str | None = None, pretty: bool = False) -> int:
    try:
        settings = load_settings(Path(env) if env else None)
        payload = OKFRagRetriever(settings).refresh_index(settings.artifacts_dir, mode=mode)
    except (RagConfigError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    _json_dump(payload, pretty=pretty)
    return 0


def rag_retrieve(
    query: str,
    *,
    env: str | None = None,
    limit: int | None = None,
    type_filter: str | None = None,
    tag: str | None = None,
    answer: bool = False,
    mode: str | None = None,
    pretty: bool = False,
) -> int:
    try:
        settings = load_settings(Path(env) if env else None)
        retriever = OKFRagRetriever(settings)
        if answer:
            payload = retriever.answer(query, limit=limit or settings.answer_evidence_limit, mode=mode)
        else:
            payload = retriever.retrieve(
                query,
                limit=limit or settings.retrieval_result_limit,
                type_filter=type_filter,
                tag=tag,
                mode=mode,
            )
    except (RagConfigError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    _json_dump(payload, pretty=pretty)
    return 0


def _types_by_stage(registry: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in registry.get("artifact_types", []):
        grouped[str(item.get("stage") or "")].append(dict(item))
    for items in grouped.values():
        items.sort(key=lambda item: str(item.get("type") or ""))
    return dict(grouped)


def render_7d_validation(payload: dict[str, Any]) -> str:
    lines = [
        "# 7D Validation",
        "",
        f"Status: {'OK' if payload.get('ok') else 'FAILED'}",
        f"Mapped artifact concepts: {payload.get('mapped_concept_count', 0)}",
        f"Unmapped concepts: {payload.get('unmapped_concept_count', 0)}",
        f"Registered artifact types: {payload.get('registered_artifact_type_count', 0)}",
        f"Required lifecycle artifact types: {payload.get('required_artifact_type_count', 0)}",
        f"Stages: {payload.get('stage_count', 0)}",
        "",
    ]
    if payload.get("errors"):
        lines += ["## Errors", ""] + [f"- {item}" for item in payload["errors"]] + [""]
    if payload.get("unmapped_concepts"):
        lines += ["## Unmapped concepts", ""]
        for item in payload["unmapped_concepts"]:
            lines.append(f"- `{item['path']}` — `{item['type']}`")
        lines.append("")
    if payload.get("warnings"):
        lines += ["## Warnings", ""] + [f"- {item}" for item in payload["warnings"]] + [""]
    return "\n".join(lines).rstrip() + "\n"


def render_7d_registry(payload: dict[str, Any]) -> str:
    stages = {str(item["key"]): item for item in payload.get("stages", [])}
    grouped = _types_by_stage(payload)
    lines = ["# 7D Registry", ""]
    for stage in sorted(stages.values(), key=lambda item: int(item.get("order") or 0)):
        key = str(stage["key"])
        lines += [f"## {stage['order']}. {stage['name']}", "", str(stage.get("description") or ""), ""]
        for item in grouped.get(key, []):
            responsible = ", ".join(item.get("responsible") or [])
            lines.append(f"- `{item['type']}` — R: {responsible}; A: {item.get('accountable')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_7d_feature_status(payload: dict[str, Any]) -> str:
    concept = payload["concept"]
    stage = payload.get("derived_stage")
    lines = [
        "# 7D Feature Status",
        "",
        f"Concept: `{concept['id']}` — {concept.get('title') or concept['id']}",
        f"Derived stage: {stage.get('stage_name') if stage else 'None'}",
        f"Artifact count: {payload.get('artifact_count', 0)}",
        f"Gap count: {payload.get('gap_count', 0)}",
        "",
    ]
    if payload.get("artifacts"):
        lines += ["## Artifacts", ""]
        for item in payload["artifacts"]:
            sd = item.get("seven_d") or {}
            lines.append(
                f"- `{item['id']}` — `{item.get('type')}` -> {sd.get('stage_name')} "
                f"({', '.join(item.get('relationship') or [])})"
            )
        lines.append("")
    if payload.get("gaps"):
        lines += ["## Gaps", ""]
        for item in payload["gaps"]:
            lines.append(f"- `{item['id']}` — {item.get('reason')}")
        lines.append("")
    lines.append(str(payload.get("note") or ""))
    return "\n".join(lines).rstrip() + "\n"


def _print_payload(payload: dict[str, Any], as_json: bool, renderer: Callable[[dict[str, Any]], str]) -> None:
    if as_json:
        _json_dump(payload, pretty=True)
    else:
        print(renderer(payload), end="")


def seven_d_report(*, bundle_path: str = "okf", stage: str | None = None, as_json: bool = False) -> int:
    try:
        bundle = OKFBundle(bundle_path)
        payload = bundle.seven_d_stage_report(stage=stage)
    except (OKFError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if as_json:
        _json_dump(payload, pretty=True)
    else:
        print(bundle.render_seven_d_stage_report(stage=stage), end="")
    return 0


def seven_d_validate(*, bundle_path: str = "okf", as_json: bool = False) -> int:
    try:
        payload = OKFBundle(bundle_path).validate_7d()
    except (OKFError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    _print_payload(payload, as_json, render_7d_validation)
    return 0 if payload.get("ok") else 1


def seven_d_registry(*, bundle_path: str = "okf", as_json: bool = False) -> int:
    try:
        payload = OKFBundle(bundle_path).seven_d_registry()
    except (OKFError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    _print_payload(payload, as_json, render_7d_registry)
    return 0


def seven_d_dashboard(*, bundle_path: str = "okf", out: str = "artifacts/7d-dashboard.html", as_json: bool = False) -> int:
    try:
        payload = OKFBundle(bundle_path).write_seven_d_dashboard_html(out)
    except (OKFError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if as_json:
        _json_dump(payload, pretty=True)
    else:
        print(
            "Wrote 7D Kanban dashboard: "
            f"{payload['path']} ({payload['stage_count']} stages, {payload['gap_count']} gaps)"
        )
    return 0


def seven_d_status(concept_id: str, *, bundle_path: str = "okf", as_json: bool = False) -> int:
    try:
        payload = OKFBundle(bundle_path).seven_d_feature_status(concept_id)
    except (OKFError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    _print_payload(payload, as_json, render_7d_feature_status)
    return 0


class Transport(str, Enum):
    stdio = "stdio"
    http = "http"
    sse = "sse"


class RagMode(str, Enum):
    local = "local"
    keyword = "keyword"
    semantic = "semantic"
    hybrid = "hybrid"


app = typer.Typer(help="Simple OKF multi-app CLI", rich_markup_mode="markdown")
rag_app = typer.Typer(help="Inspect, refresh, and query the local OKF RAG index", rich_markup_mode="markdown")
seven_d_app = typer.Typer(help="Work with the Simple OKF 7D registry", rich_markup_mode="markdown")
app.add_typer(rag_app, name="rag")
app.add_typer(seven_d_app, name="7d")


BundleArg = Annotated[Path, typer.Argument(help="Path to OKF bundle")]
BundleOption = Annotated[str, typer.Option("--bundle", help="Path to OKF bundle")]
JsonOption = Annotated[bool, typer.Option("--json", help="Print JSON instead of Markdown")]
PrettyOption = Annotated[bool, typer.Option("--pretty", help="Pretty-print JSON")]
EnvOption = Annotated[str | None, typer.Option("--env", help="Path to okf_mcp/rag/.env file")]
RagModeOption = Annotated[RagMode | None, typer.Option("--mode", help="RAG retrieval mode")]


def _exit(code: int) -> None:
    raise typer.Exit(code=int(code or 0))


def _mode_value(mode: RagMode | None) -> str | None:
    return mode.value if mode else None


@app.command("server", help="Run the OKF FastMCP server")
def server_command(
    bundle: Annotated[str, typer.Option("--bundle", help="Path to the OKF bundle directory")] = DEFAULT_BUNDLE,
    transport: Annotated[Transport, typer.Option("--transport", help="MCP transport to use")] = Transport.stdio,
    host: Annotated[str, typer.Option("--host", help="Host for HTTP/SSE transports")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Port for HTTP/SSE transports")] = 8000,
) -> None:
    _exit(_run_server(bundle=bundle, transport=transport.value, host=host, port=port))


@app.command("validate", help="Validate an OKF bundle")
def validate_command(bundle: BundleArg = Path("okf")) -> None:
    _exit(validate_bundle(bundle))


@app.command("indexes", help="Generate OKF index.md files")
def indexes_command(bundle: BundleArg = Path("okf")) -> None:
    _exit(generate_indexes(bundle))


@app.command("export", help="Export Markdown docs into OKF Source Document concepts")
def export_command(
    source: Annotated[Path, typer.Argument(help="Canonical Markdown source directory")] = Path("system"),
    source_option: Annotated[Path | None, typer.Option("--source", help="Canonical Markdown source directory")] = None,
    out: Annotated[Path, typer.Option("--out", help="OKF bundle or documents output directory")] = Path("okf"),
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing generated concepts")] = False,
) -> None:
    _exit(export_documents(source_option or source, out, force=force))


@app.command("graph", help="Generate OKF graph JSON/HTML from Markdown links")
def graph_command(
    bundle: BundleArg = Path("okf"),
    out: Annotated[str | None, typer.Option("--out", help="Output JSON artifact path under repository artifacts/. Defaults to stdout.")] = None,
    html_out: Annotated[str | None, typer.Option("--html-out", help="Output self-contained HTML report artifact path under artifacts/.")] = None,
    pretty: Annotated[bool, typer.Option("--pretty", help="Pretty-print JSON output")] = False,
) -> None:
    _exit(generate_graph(bundle, out=out, html_out=html_out, pretty=pretty))


@rag_app.command("inspect", help="Inspect OKF RAG corpus")
def rag_inspect_command(env: EnvOption = None, pretty: PrettyOption = False) -> None:
    _exit(rag_inspect(env=env, pretty=pretty))


@rag_app.command("refresh", help="Refresh local OKF RAG index")
def rag_refresh_command(
    env: EnvOption = None,
    pretty: PrettyOption = False,
    mode: RagModeOption = None,
) -> None:
    _exit(rag_refresh(env=env, mode=_mode_value(mode), pretty=pretty))


@rag_app.command("retrieve", help="Retrieve OKF RAG chunks")
def rag_retrieve_command(
    query: Annotated[str, typer.Argument(help="Search query")],
    env: EnvOption = None,
    limit: Annotated[int | None, typer.Option("--limit", help="Maximum result count")] = None,
    type_filter: Annotated[str | None, typer.Option("--type-filter", help="Filter by OKF concept type")] = None,
    tag: Annotated[str | None, typer.Option("--tag", help="Filter by tag")] = None,
    answer: Annotated[bool, typer.Option("--answer", help="Return extractive answer instead of raw hits")] = False,
    mode: RagModeOption = None,
    pretty: PrettyOption = False,
) -> None:
    _exit(
        rag_retrieve(
            query,
            env=env,
            limit=limit,
            type_filter=type_filter,
            tag=tag,
            answer=answer,
            mode=_mode_value(mode),
            pretty=pretty,
        )
    )


@seven_d_app.command("report", help="Generate a report for every 7D stage")
def seven_d_report_command(
    bundle: BundleOption = "okf",
    as_json: JsonOption = False,
    stage: Annotated[str | None, typer.Option("--stage", help="Optional 7D stage key or display name")] = None,
) -> None:
    _exit(seven_d_report(bundle_path=bundle, stage=stage, as_json=as_json))


@seven_d_app.command("validate", help="Validate 7D registry usage")
def seven_d_validate_command(bundle: BundleOption = "okf", as_json: JsonOption = False) -> None:
    _exit(seven_d_validate(bundle_path=bundle, as_json=as_json))


@seven_d_app.command("registry", help="Print the 7D registry")
def seven_d_registry_command(bundle: BundleOption = "okf", as_json: JsonOption = False) -> None:
    _exit(seven_d_registry(bundle_path=bundle, as_json=as_json))


@seven_d_app.command("dashboard", help="Write the interactive 7D Kanban dashboard HTML")
def seven_d_dashboard_command(
    bundle: BundleOption = "okf",
    out: Annotated[str, typer.Option("--out", help="Repository artifacts/ output HTML path")] = "artifacts/7d-dashboard.html",
    as_json: JsonOption = False,
) -> None:
    _exit(seven_d_dashboard(bundle_path=bundle, out=out, as_json=as_json))


def _seven_d_status_command(concept_id: Annotated[str, typer.Argument(help="OKF concept ID")], bundle: BundleOption = "okf", as_json: JsonOption = False) -> None:
    _exit(seven_d_status(concept_id, bundle_path=bundle, as_json=as_json))


seven_d_app.command("status", help="Derive one concept's 7D feature status")(_seven_d_status_command)
seven_d_app.command("feature-status", help="Derive one concept's 7D feature status")(_seven_d_status_command)


def _invoke_typer(typer_app: typer.Typer, argv: Sequence[str] | None = None, *, prog_name: str | None = None) -> int:
    command = typer.main.get_command(typer_app)
    try:
        result = command.main(args=list(argv or []), prog_name=prog_name, standalone_mode=True)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    return int(result or 0)


def _run_server(*, bundle: str = DEFAULT_BUNDLE, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000) -> int:
    try:
        settings = load_settings()
        readiness = check_rag_readiness(settings)
    except (RagConfigError, RagReadinessError) as exc:
        print(f"ERROR: MCP startup readiness failed: {exc}", file=sys.stderr)
        return 2
    print(
        "RAG infrastructure readiness OK: "
        + ", ".join(str(item.get("name")) for item in readiness.get("probes", [])),
        file=sys.stderr,
    )
    create_mcp = _load_create_mcp()
    mcp = create_mcp(bundle)
    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=transport, host=host, port=port)
    return 0


server_app = typer.Typer(help="Run an OKF FastMCP server", rich_markup_mode="markdown")
server_app.command()(server_command)
validate_app = typer.Typer(help="Validate an OKF bundle", rich_markup_mode="markdown")
validate_app.command()(validate_command)
indexes_app = typer.Typer(help="Generate OKF index.md files", rich_markup_mode="markdown")
indexes_app.command()(indexes_command)
export_app = typer.Typer(help="Export Markdown docs into OKF Source Document concepts", rich_markup_mode="markdown")
export_app.command()(export_command)
graph_app = typer.Typer(help="Generate OKF graph JSON/HTML from Markdown links", rich_markup_mode="markdown")
graph_app.command()(graph_command)
rag_inspect_app = typer.Typer(help="Inspect OKF RAG corpus", rich_markup_mode="markdown")
rag_inspect_app.command()(rag_inspect_command)
rag_refresh_app = typer.Typer(help="Refresh local OKF RAG index", rich_markup_mode="markdown")
rag_refresh_app.command()(rag_refresh_command)
rag_retrieve_app = typer.Typer(help="Retrieve OKF RAG chunks", rich_markup_mode="markdown")
rag_retrieve_app.command()(rag_retrieve_command)


def main(
    argv: Sequence[str] | None = None,
    *,
    multi_app_help_for_options: bool = True,
) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    # Backward compatibility for the old `python -m okf_mcp --bundle okf` server CLI.
    # Console `okf --help` opts into multi-app help.
    if not args_list or (args_list[0].startswith("-") and not (multi_app_help_for_options and args_list[0] in {"-h", "--help"})):
        return server_main(args_list)
    return _invoke_typer(app, args_list)


def server_main(argv: Sequence[str] | None = None) -> int:
    return _invoke_typer(server_app, sys.argv[1:] if argv is None else argv, prog_name="okf-mcp")


def validate_main(argv: Sequence[str] | None = None) -> int:
    return _invoke_typer(validate_app, sys.argv[1:] if argv is None else argv, prog_name="okf-validate")


def indexes_main(argv: Sequence[str] | None = None) -> int:
    return _invoke_typer(indexes_app, sys.argv[1:] if argv is None else argv, prog_name="okf-generate-indexes")


def export_main(argv: Sequence[str] | None = None) -> int:
    return _invoke_typer(export_app, sys.argv[1:] if argv is None else argv, prog_name="okf-export")


def graph_main(argv: Sequence[str] | None = None) -> int:
    return _invoke_typer(graph_app, sys.argv[1:] if argv is None else argv, prog_name="okf-generate-graph")


def rag_inspect_main(argv: Sequence[str] | None = None) -> int:
    return _invoke_typer(rag_inspect_app, sys.argv[1:] if argv is None else argv, prog_name="okf-rag-inspect")


def rag_refresh_main(argv: Sequence[str] | None = None) -> int:
    return _invoke_typer(rag_refresh_app, sys.argv[1:] if argv is None else argv, prog_name="okf-rag-refresh")


def rag_retrieve_main(argv: Sequence[str] | None = None) -> int:
    return _invoke_typer(rag_retrieve_app, sys.argv[1:] if argv is None else argv, prog_name="okf-rag-retrieve")


def seven_d_main(argv: Sequence[str] | None = None) -> int:
    return _invoke_typer(seven_d_app, sys.argv[1:] if argv is None else argv, prog_name="okf-7d")


if __name__ == "__main__":
    raise SystemExit(main())
