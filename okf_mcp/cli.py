from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Sequence
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


def _add_bundle_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bundle", default="okf", help="Path to OKF bundle")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown")


def _add_seven_d_subcommands(parser: argparse.ArgumentParser) -> None:
    seven_sub = parser.add_subparsers(dest="seven_d_command", required=True)

    report = seven_sub.add_parser("report", help="Generate a report for every 7D stage")
    _add_bundle_json(report)
    report.add_argument("--stage", default=None, help="Optional 7D stage key or display name")
    report.set_defaults(handler=lambda args: seven_d_report(bundle_path=args.bundle, stage=args.stage, as_json=args.json))

    validate_7d = seven_sub.add_parser("validate", help="Validate 7D registry usage")
    _add_bundle_json(validate_7d)
    validate_7d.set_defaults(handler=lambda args: seven_d_validate(bundle_path=args.bundle, as_json=args.json))

    registry = seven_sub.add_parser("registry", help="Print the 7D registry")
    _add_bundle_json(registry)
    registry.set_defaults(handler=lambda args: seven_d_registry(bundle_path=args.bundle, as_json=args.json))

    dashboard = seven_sub.add_parser("dashboard", help="Write the interactive 7D Kanban dashboard HTML")
    dashboard.add_argument("--bundle", default="okf", help="Path to OKF bundle")
    dashboard.add_argument("--out", default="artifacts/7d-dashboard.html", help="Repository artifacts/ output HTML path")
    dashboard.add_argument("--json", action="store_true", help="Print JSON instead of a short message")
    dashboard.set_defaults(handler=lambda args: seven_d_dashboard(bundle_path=args.bundle, out=args.out, as_json=args.json))

    for name in ("status", "feature-status"):
        status = seven_sub.add_parser(name, help="Derive one concept's 7D feature status")
        _add_bundle_json(status)
        status.add_argument("concept_id", help="OKF concept ID")
        status.set_defaults(handler=lambda args: seven_d_status(args.concept_id, bundle_path=args.bundle, as_json=args.json))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple OKF multi-app CLI")
    sub = parser.add_subparsers(dest="app", required=True)

    server = sub.add_parser("server", help="Run the OKF FastMCP server")
    server.add_argument("--bundle", default=DEFAULT_BUNDLE, help="Path to the OKF bundle directory")
    server.add_argument("--transport", default="stdio", choices=("stdio", "http", "sse"), help="MCP transport to use")
    server.add_argument("--host", default="127.0.0.1", help="Host for HTTP/SSE transports")
    server.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE transports")
    server.set_defaults(handler=lambda args: _run_server(args))

    validate = sub.add_parser("validate", help="Validate an OKF bundle")
    validate.add_argument("bundle", nargs="?", default="okf")
    validate.set_defaults(handler=lambda args: validate_bundle(Path(args.bundle)))

    indexes = sub.add_parser("indexes", help="Generate OKF index.md files")
    indexes.add_argument("bundle", nargs="?", default="okf")
    indexes.set_defaults(handler=lambda args: generate_indexes(Path(args.bundle)))

    export = sub.add_parser("export", help="Export Markdown docs into OKF Source Document concepts")
    export.add_argument("source", nargs="?", default="system", help="Canonical Markdown source directory")
    export.add_argument("--source", dest="source_option", default=None, help="Canonical Markdown source directory")
    export.add_argument("--out", default="okf", help="OKF bundle or documents output directory")
    export.add_argument("--force", action="store_true", help="Overwrite existing generated concepts")
    export.set_defaults(handler=lambda args: export_documents(Path(args.source_option or args.source), Path(args.out), force=args.force))

    graph = sub.add_parser("graph", help="Generate OKF graph JSON/HTML from Markdown links")
    graph.add_argument("bundle", nargs="?", default="okf")
    graph.add_argument("--out", help="Output JSON artifact path under repository artifacts/. Defaults to stdout.")
    graph.add_argument("--html-out", help="Output self-contained HTML report artifact path under artifacts/.")
    graph.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    graph.set_defaults(handler=lambda args: generate_graph(Path(args.bundle), out=args.out, html_out=args.html_out, pretty=args.pretty))

    rag = sub.add_parser("rag", help="Inspect, refresh, and query the local OKF RAG index")
    rag_sub = rag.add_subparsers(dest="rag_command", required=True)
    rag_inspect_parser = rag_sub.add_parser("inspect", help="Inspect OKF RAG corpus")
    rag_inspect_parser.add_argument("--env", default=None, help="Path to okf_mcp/rag/.env file")
    rag_inspect_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    rag_inspect_parser.set_defaults(handler=lambda args: rag_inspect(env=args.env, pretty=args.pretty))

    rag_refresh_parser = rag_sub.add_parser("refresh", help="Refresh local OKF RAG index")
    rag_refresh_parser.add_argument("--env", default=None, help="Path to okf_mcp/rag/.env file")
    rag_refresh_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    rag_refresh_parser.add_argument("--mode", choices=("local", "keyword", "semantic", "hybrid"), default=None)
    rag_refresh_parser.set_defaults(handler=lambda args: rag_refresh(env=args.env, mode=args.mode, pretty=args.pretty))

    rag_retrieve_parser = rag_sub.add_parser("retrieve", help="Retrieve OKF RAG chunks")
    rag_retrieve_parser.add_argument("query")
    rag_retrieve_parser.add_argument("--env", default=None, help="Path to okf_mcp/rag/.env file")
    rag_retrieve_parser.add_argument("--limit", type=int, default=None)
    rag_retrieve_parser.add_argument("--type-filter", default=None)
    rag_retrieve_parser.add_argument("--tag", default=None)
    rag_retrieve_parser.add_argument("--answer", action="store_true", help="Return extractive answer instead of raw hits")
    rag_retrieve_parser.add_argument("--mode", choices=("local", "keyword", "semantic", "hybrid"), default=None)
    rag_retrieve_parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    rag_retrieve_parser.set_defaults(
        handler=lambda args: rag_retrieve(
            args.query,
            env=args.env,
            limit=args.limit,
            type_filter=args.type_filter,
            tag=args.tag,
            answer=args.answer,
            mode=args.mode,
            pretty=args.pretty,
        )
    )

    seven = sub.add_parser("7d", help="Work with the Simple OKF 7D registry")
    _add_seven_d_subcommands(seven)

    return parser


def _run_server(args: argparse.Namespace) -> int:
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
    mcp = create_mcp(args.bundle)
    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)
    return 0


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
    parser = build_parser()
    args = parser.parse_args(args_list)
    return int(args.handler(args) or 0)


def server_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an OKF FastMCP server")
    parser.add_argument("--bundle", default=DEFAULT_BUNDLE, help="Path to the OKF bundle directory")
    parser.add_argument("--transport", default="stdio", choices=("stdio", "http", "sse"), help="MCP transport to use")
    parser.add_argument("--host", default="127.0.0.1", help="Host for HTTP/SSE transports")
    parser.add_argument("--port", type=int, default=8000, help="Port for HTTP/SSE transports")
    return _run_server(parser.parse_args(argv))


def validate_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an OKF bundle")
    parser.add_argument("bundle", nargs="?", default="okf")
    args = parser.parse_args(argv)
    return validate_bundle(Path(args.bundle))


def indexes_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate OKF index.md files")
    parser.add_argument("bundle", nargs="?", default="okf")
    args = parser.parse_args(argv)
    return generate_indexes(Path(args.bundle))


def export_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export Markdown docs into OKF Source Document concepts")
    parser.add_argument("source", nargs="?", default="system", help="Canonical Markdown source directory")
    parser.add_argument("--source", dest="source_option", default=None, help="Canonical Markdown source directory")
    parser.add_argument("--out", default="okf", help="OKF bundle or documents output directory")
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated concepts")
    args = parser.parse_args(argv)
    return export_documents(Path(args.source_option or args.source), Path(args.out), force=args.force)


def graph_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate OKF graph JSON/HTML from Markdown links")
    parser.add_argument("bundle", nargs="?", default="okf")
    parser.add_argument("--out", help="Output JSON artifact path under repository artifacts/. Defaults to stdout.")
    parser.add_argument("--html-out", help="Output self-contained HTML report artifact path under artifacts/.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args(argv)
    return generate_graph(Path(args.bundle), out=args.out, html_out=args.html_out, pretty=args.pretty)


def rag_inspect_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect OKF RAG corpus")
    parser.add_argument("--env", default=None, help="Path to okf_mcp/rag/.env file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args(argv)
    return rag_inspect(env=args.env, pretty=args.pretty)


def rag_refresh_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh local OKF RAG index")
    parser.add_argument("--env", default=None, help="Path to okf_mcp/rag/.env file")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--mode", choices=("local", "keyword", "semantic", "hybrid"), default=None)
    args = parser.parse_args(argv)
    return rag_refresh(env=args.env, mode=args.mode, pretty=args.pretty)


def rag_retrieve_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retrieve OKF RAG chunks")
    parser.add_argument("query")
    parser.add_argument("--env", default=None, help="Path to okf_mcp/rag/.env file")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--type-filter", default=None)
    parser.add_argument("--tag", default=None)
    parser.add_argument("--answer", action="store_true", help="Return extractive answer instead of raw hits")
    parser.add_argument("--mode", choices=("local", "keyword", "semantic", "hybrid"), default=None)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = parser.parse_args(argv)
    return rag_retrieve(
        args.query,
        env=args.env,
        limit=args.limit,
        type_filter=args.type_filter,
        tag=args.tag,
        answer=args.answer,
        mode=args.mode,
        pretty=args.pretty,
    )


def seven_d_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Work with the Simple OKF 7D registry")
    _add_seven_d_subcommands(parser)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    return int(args.handler(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
