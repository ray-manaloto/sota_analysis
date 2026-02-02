#!/usr/bin/env python3
"""Emit an OpenTelemetry span around an external command."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def ensure_otel():
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # noqa: F401
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource  # noqa: F401
        from opentelemetry.sdk.trace import TracerProvider  # noqa: F401
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: F401
        from opentelemetry.trace import SpanKind, Status, StatusCode  # noqa: F401
    except ModuleNotFoundError:
        if os.getenv("TITAN_NO_INSTALL") == "1":
            raise SystemExit("OpenTelemetry SDK missing and TITAN_NO_INSTALL=1")
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "opentelemetry-sdk",
                "opentelemetry-exporter-otlp",
            ]
        )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.trace import SpanKind, Status, StatusCode

    return OTLPSpanExporter, Resource, TracerProvider, SimpleSpanProcessor, SpanKind, Status, StatusCode


def main() -> None:
    parser = argparse.ArgumentParser(description="Wrap a command in an OTEL span.")
    parser.add_argument("--name", required=True, help="Span name to emit.")
    parser.add_argument("--tool", help="Tool name for span attributes.")
    parser.add_argument("--phase", help="Tool phase (e.g., run, loop, index).")
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to execute.")
    args = parser.parse_args()

    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        raise SystemExit("No command provided.")

    OTLPSpanExporter, Resource, TracerProvider, SimpleSpanProcessor, SpanKind, Status, StatusCode = ensure_otel()

    service_name = os.getenv("OTEL_SERVICE_NAME", "titan-protocol")
    deployment_env = os.getenv("OTEL_DEPLOYMENT_ENVIRONMENT")
    resource_attrs = {"service.name": service_name}
    if deployment_env:
        resource_attrs["deployment.environment"] = deployment_env

    provider = TracerProvider(resource=Resource.create(resource_attrs))
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))

    from opentelemetry import trace

    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("titan_protocol.otel_span")

    command_line = " ".join(cmd)
    executable_name = Path(cmd[0]).name

    with tracer.start_as_current_span(args.name, kind=SpanKind.CLIENT) as span:
        span.set_attribute("process.command_line", command_line)
        span.set_attribute("process.executable.name", executable_name)
        if args.tool:
            span.set_attribute("tool.name", args.tool)
        if args.phase:
            span.set_attribute("tool.phase", args.phase)
        result = subprocess.run(cmd, check=False)
        span.set_attribute("process.exit.code", result.returncode)
        if result.returncode != 0:
            span.set_status(Status(StatusCode.ERROR))

    provider.shutdown()
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
