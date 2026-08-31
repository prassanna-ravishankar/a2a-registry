#!/usr/bin/env python3
"""Read-only heuristic security audit of every registered A2A Agent Card.

The default report deliberately excludes card-authored text. Findings are leads
for human review, not proof of abuse and not authorization to mutate registry
data.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse

DEFAULT_API_BASE = "https://a2aregistry.org/api"
DEFAULT_CONCURRENCY = 12
DEFAULT_TIMEOUT = 10.0
MAX_BODY_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 3
USER_AGENT = "A2A-Registry-CardAudit/1.0"

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}
SUSPICIOUS_HOST_SUFFIXES = (
    ".ngrok-free.app",
    ".ngrok.io",
    ".trycloudflare.com",
    ".loca.lt",
    ".localtunnel.me",
)


@dataclass(frozen=True)
class Rule:
    rule_id: str
    severity: str
    description: str
    pattern: re.Pattern[str]


TEXT_RULES = (
    Rule(
        "prompt.override",
        "high",
        "Text attempts to override or disregard prior instructions.",
        re.compile(
            r"\b(?:ignore|disregard|override|forget)\b.{0,80}"
            r"\b(?:previous|prior|above|system|developer)\b.{0,30}\binstructions?\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    Rule(
        "prompt.secret_exfiltration",
        "medium",
        "Text requests disclosure or transmission of secrets or credentials.",
        re.compile(
            r"\b(?:reveal|print|return|send|upload|exfiltrat\w*)\b.{0,100}"
            r"\b(?:secret|token|credential|password|api[ _-]?key|environment variable)s?\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    Rule(
        "prompt.role_impersonation",
        "medium",
        "Text contains a role or instruction boundary commonly used in prompt injection.",
        re.compile(
            r"(?:^|[\r\n])\s*(?:#{1,6}\s*)?"
            r"(?:system|developer|assistant)\s*(?:message|instructions?)?\s*:"
            r".{0,120}\b(?:ignore|disregard|override|reveal|execute|exfiltrat\w*)\b",
            re.IGNORECASE | re.MULTILINE | re.DOTALL,
        ),
    ),
    Rule(
        "prompt.tool_coercion",
        "medium",
        "Text directs a model to invoke tools or execute commands.",
        re.compile(
            r"\b(?:must|immediately|silently|always)\b.{0,70}"
            r"\b(?:call|invoke|run|execute)\b.{0,30}"
            r"\b(?:tool|command|shell|terminal|function)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    description: str
    path: str
    value_sha256: str
    snippet: str | None = None


@dataclass
class CardResult:
    agent_id: str
    card_url_sha256: str
    findings: list[Finding]
    fetch_status: str = "ok"
    http_status: int | None = None


def fingerprint(value: Any) -> str:
    if isinstance(value, str):
        raw = value.encode("utf-8", errors="replace")
    else:
        raw = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def safe_key(key: Any) -> str:
    text = str(key)
    if re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", text):
        return text
    return f"<key:{fingerprint(text)[:12]}>"


def walk_strings(value: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from walk_strings(child, f"{path}.{safe_key(key)}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk_strings(child, f"{path}[{index}]")


def make_snippet(value: str) -> str:
    collapsed = re.sub(r"\s+", " ", value).strip()[:160]
    return collapsed.encode("unicode_escape", errors="backslashreplace").decode("ascii")


def add_finding(
    findings: list[Finding],
    rule_id: str,
    severity: str,
    description: str,
    path: str,
    value: Any,
    include_snippets: bool,
) -> None:
    findings.append(
        Finding(
            rule_id=rule_id,
            severity=severity,
            description=description,
            path=path,
            value_sha256=fingerprint(value),
            snippet=make_snippet(value) if include_snippets and isinstance(value, str) else None,
        )
    )


def audit_card(card: Any, include_snippets: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(card, dict):
        add_finding(
            findings,
            "structure.card_not_object",
            "high",
            "The Agent Card root is not a JSON object.",
            "$",
            card,
            include_snippets,
        )
        return findings

    skills = card.get("skills")
    if skills is not None and not isinstance(skills, list):
        add_finding(
            findings,
            "structure.skills_not_array",
            "high",
            "The skills field is not an array.",
            "$.skills",
            skills,
            include_snippets,
        )
    elif isinstance(skills, list):
        if len(skills) > 200:
            add_finding(
                findings,
                "volume.excessive_skills",
                "medium",
                "The card contains more than 200 skills.",
                "$.skills",
                len(skills),
                include_snippets,
            )
        for index, skill in enumerate(skills):
            if not isinstance(skill, dict):
                add_finding(
                    findings,
                    "structure.skill_not_object",
                    "high",
                    "A skill entry is not an object.",
                    f"$.skills[{index}]",
                    skill,
                    include_snippets,
                )
                continue
            for field in ("tags", "examples", "inputModes", "outputModes"):
                value = skill.get(field)
                if value is not None and (
                    not isinstance(value, list)
                    or any(not isinstance(item, str) for item in value)
                ):
                    add_finding(
                        findings,
                        "structure.non_string_array_item",
                        "high",
                        f"{field} must be an array of strings.",
                        f"$.skills[{index}].{field}",
                        value,
                        include_snippets,
                    )

    for path, text in walk_strings(card):
        if len(text) > 20_000:
            add_finding(
                findings,
                "volume.very_long_text",
                "medium",
                "A single text value exceeds 20,000 characters.",
                path,
                text,
                include_snippets,
            )
        if re.search(
            r"[\u00ad\u200b-\u200f\u202a-\u202e\u2060-\u2069\ufeff\U000e0000-\U000e007f]",
            text,
        ):
            add_finding(
                findings,
                "obfuscation.invisible_unicode",
                "medium",
                "Text contains invisible or bidirectional control characters.",
                path,
                text,
                include_snippets,
            )
        if (
            not path.startswith("$.signatures[")
            and not path.endswith((".protected", ".jws"))
            and re.search(r"(?:[A-Za-z0-9+/_-]{160,}={0,2})", text)
        ):
            add_finding(
                findings,
                "obfuscation.encoded_blob",
                "low",
                "Text contains a long base64-like run.",
                path,
                text,
                include_snippets,
            )
        for rule in TEXT_RULES:
            if rule.pattern.search(text):
                add_finding(
                    findings,
                    rule.rule_id,
                    rule.severity,
                    rule.description,
                    path,
                    text,
                    include_snippets,
                )

    endpoint = card.get("url")
    if isinstance(endpoint, str):
        hostname = (urlparse(endpoint).hostname or "").lower()
        if hostname.endswith(SUSPICIOUS_HOST_SUFFIXES):
            add_finding(
                findings,
                "endpoint.ephemeral_tunnel",
                "low",
                "The agent endpoint uses a commonly ephemeral tunnel domain.",
                "$.url",
                endpoint,
                include_snippets,
            )

    return findings


def resolve_public_addresses(url: str) -> tuple[str, int, list[str]]:
    parsed = urlparse(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("blocked_url")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(
            parsed.hostname,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
    except OSError:
        raise ValueError("dns_error") from None
    except ValueError:
        raise ValueError("blocked_url") from None
    addresses = list(dict.fromkeys(item[4][0] for item in infos))
    if not addresses:
        raise ValueError("blocked_url")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("blocked_url")
    return parsed.hostname, port, addresses


def public_http_url(url: str) -> bool:
    try:
        resolve_public_addresses(url)
        return True
    except ValueError:
        return False


def request_pinned(
    url: str,
    hostname: str,
    port: int,
    addresses: list[str],
    timeout: float,
) -> tuple[http.client.HTTPResponse, http.client.HTTPConnection]:
    """Connect to a vetted numeric IP while retaining HTTP Host and TLS SNI."""
    parsed = urlparse(url)
    target = parsed.path or "/"
    if parsed.query:
        target += f"?{parsed.query}"
    default_port = 443 if parsed.scheme == "https" else 80
    display_host = f"[{hostname}]" if ":" in hostname else hostname
    host_header = display_host if port == default_port else f"{display_host}:{port}"
    last_error: OSError | None = None

    for address in addresses:
        connection = http.client.HTTPConnection(address, port=port, timeout=timeout)
        try:
            if parsed.scheme == "https":
                raw_socket = socket.create_connection((address, port), timeout=timeout)
                context = ssl.create_default_context()
                connection.sock = context.wrap_socket(raw_socket, server_hostname=hostname)
            connection.request(
                "GET",
                target,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                    "Host": host_header,
                },
            )
            return connection.getresponse(), connection
        except OSError as error:
            last_error = error
            connection.close()

    raise last_error or OSError("no vetted address was reachable")


def fetch_json(url: str, timeout: float, validate_public: bool = True) -> tuple[Any, int]:
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        if validate_public:
            hostname, port, addresses = resolve_public_addresses(current)
        else:
            parsed = urlparse(current)
            if not parsed.hostname:
                raise ValueError("blocked_url")
            hostname = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            addresses = [hostname]

        # request_pinned receives only the addresses resolved and validated above;
        # it never resolves the attacker-controlled hostname a second time.
        response, connection = request_pinned(
            current, hostname, port, addresses, timeout
        )
        try:
            status = response.status
            if 300 <= status < 400:
                location = response.getheader("Location")
                if not location:
                    raise ValueError("redirect_without_location")
                current = urljoin(current, location)
                continue
            if status != 200:
                raise FetchHTTPError(status)
            content_length = response.getheader("Content-Length")
            if content_length and int(content_length) > MAX_BODY_BYTES:
                raise ValueError("body_too_large")
            chunks: list[bytes] = []
            size = 0
            while chunk := response.read(64 * 1024):
                size += len(chunk)
                if size > MAX_BODY_BYTES:
                    raise ValueError("body_too_large")
                chunks.append(chunk)
            return json.loads(b"".join(chunks)), status
        finally:
            connection.close()
    raise ValueError("too_many_redirects")


class FetchHTTPError(Exception):
    def __init__(self, status: int):
        super().__init__(status)
        self.status = status


def fetch_agents(api_base: str, timeout: float, agent_id: str | None = None) -> list[dict]:
    if agent_id:
        data, _ = fetch_json(f"{api_base.rstrip('/')}/agents/{agent_id}", timeout)
        return [data]

    agents: list[dict] = []
    offset = 0
    limit = 100
    for _page in range(1000):
        data, _ = fetch_json(
            f"{api_base.rstrip('/')}/agents?limit={limit}&offset={offset}", timeout
        )
        if not isinstance(data, dict) or not isinstance(data.get("agents"), list):
            raise ValueError("invalid_registry_response")
        batch = data["agents"]
        agents.extend(item for item in batch if isinstance(item, dict))
        if not batch or len(agents) >= data.get("total", len(agents)):
            return agents
        offset += limit
    raise ValueError("invalid_registry_response")


def classify_fetch_error(error: Exception) -> tuple[str, int | None]:
    if isinstance(error, FetchHTTPError):
        return "http_error", error.status
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "timeout", None
    if isinstance(error, OSError):
        return "network_error", None
    if isinstance(error, json.JSONDecodeError):
        return "invalid_json", None
    if isinstance(error, ValueError):
        allowed = {
            "blocked_url",
            "body_too_large",
            "dns_error",
            "redirect_without_location",
            "too_many_redirects",
        }
        return (str(error) if str(error) in allowed else "invalid_response"), None
    return "unexpected_error", None


def scan_one(agent: dict, timeout: float, include_snippets: bool) -> CardResult:
    agent_id = str(agent.get("id", "unknown"))
    url = agent.get("wellKnownURI")
    url_fingerprint = fingerprint(url if isinstance(url, str) else "")
    if not isinstance(url, str) or not url:
        return CardResult(agent_id, url_fingerprint, [], "missing_card_url")
    try:
        card, status = fetch_json(url, timeout)
        return CardResult(
            agent_id,
            url_fingerprint,
            audit_card(card, include_snippets=include_snippets),
            http_status=status,
        )
    except Exception as error:  # Each untrusted card must be isolated from the full scan.
        fetch_status, http_status = classify_fetch_error(error)
        return CardResult(agent_id, url_fingerprint, [], fetch_status, http_status)


def build_report(results: list[CardResult], api_base: str) -> dict[str, Any]:
    findings = [finding for result in results for finding in result.findings]
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_base": api_base,
        "mode": "read_only_heuristic_audit",
        "redaction": "card-authored text omitted unless --include-snippets was used",
        "summary": {
            "agents": len(results),
            "cards_fetched": sum(result.fetch_status == "ok" for result in results),
            "fetch_failures": sum(result.fetch_status != "ok" for result in results),
            "findings": len(findings),
            "by_severity": dict(sorted(Counter(f.severity for f in findings).items())),
            "by_rule": dict(sorted(Counter(f.rule_id for f in findings).items())),
        },
        "results": [
            {
                **{key: value for key, value in asdict(result).items() if key != "findings"},
                "findings": [asdict(finding) for finding in result.findings],
            }
            for result in sorted(results, key=lambda item: item.agent_id)
        ],
    }


def print_summary(report: dict[str, Any]) -> None:
    summary = report["summary"]
    print("A2A Agent Card security audit (read-only, heuristic)")
    print(
        f"Agents: {summary['agents']} | cards fetched: {summary['cards_fetched']} | "
        f"fetch failures: {summary['fetch_failures']}"
    )
    print(f"Findings: {summary['findings']} | severity: {summary['by_severity'] or '{}'}")
    print(f"Rules: {summary['by_rule'] or '{}'}")
    print("Card-authored text is redacted. Findings require human review.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--agent-id", help="Audit one registry agent UUID instead of every card")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--output", help="Write the complete JSON report to this path")
    parser.add_argument("--json", action="store_true", help="Print the JSON report")
    parser.add_argument(
        "--include-snippets",
        action="store_true",
        help="Include matched third-party text (unsafe for unattended model ingestion)",
    )
    parser.add_argument(
        "--fail-on",
        choices=("low", "medium", "high"),
        help="Exit 1 when a finding at this severity or higher exists",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.concurrency < 1 or args.timeout <= 0:
        print("concurrency and timeout must be positive", file=sys.stderr)
        return 2
    try:
        agents = fetch_agents(args.api_base, args.timeout, args.agent_id)
    except Exception as error:
        status, http_status = classify_fetch_error(error)
        suffix = f" (HTTP {http_status})" if http_status else ""
        print(f"Unable to fetch registry agents: {status}{suffix}", file=sys.stderr)
        return 2

    results: list[CardResult] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(scan_one, agent, args.timeout, args.include_snippets): agent
            for agent in agents
        }
        for future in as_completed(futures):
            results.append(future.result())

    report = build_report(results, args.api_base)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    if args.json:
        print(rendered)
    else:
        print_summary(report)

    if args.fail_on:
        threshold = SEVERITY_ORDER[args.fail_on]
        if any(
            SEVERITY_ORDER[finding.severity] >= threshold
            for result in results
            for finding in result.findings
        ):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
