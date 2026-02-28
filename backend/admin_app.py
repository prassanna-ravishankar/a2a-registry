"""Internal admin dashboard — accessed via kubectl port-forward only, never through ingress."""

import secrets
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import settings
from app.database import Database
from app.repositories import AgentRepository, FlagRepository, StatsRepository

# Session store: token -> authenticated (simple in-memory, single-pod use only)
_sessions: set[str] = set()
_SESSION_COOKIE = "admin_session"

admin_db = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await admin_db.connect()
    yield
    await admin_db.disconnect()


app = FastAPI(title="A2A Registry Admin", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _is_authenticated(request: Request) -> bool:
    token = request.cookies.get(_SESSION_COOKIE)
    return token is not None and token in _sessions


def _require_auth(request: Request) -> Optional[Response]:
    if not _is_authenticated(request):
        return RedirectResponse("/login", status_code=302)
    return None


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _page(title: str, body: str, breadcrumb: str = "") -> HTMLResponse:
    nav = """
    <nav style="background:#1a1a2e;padding:10px 20px;display:flex;gap:20px;align-items:center">
      <span style="color:#e94560;font-weight:bold;font-size:18px">A2A Admin</span>
      <a href="/" style="color:#ccc;text-decoration:none">Dashboard</a>
      <a href="/flags" style="color:#ccc;text-decoration:none">Flags</a>
      <a href="/agents" style="color:#ccc;text-decoration:none">Agents</a>
      <span style="margin-left:auto">
        <a href="/logout" style="color:#e94560;text-decoration:none;font-size:13px">Logout</a>
      </span>
    </nav>"""
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>{title} — A2A Admin</title>
<style>
  body{{font-family:monospace;background:#0f0f1a;color:#ddd;margin:0}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th{{background:#1a1a2e;padding:8px;text-align:left;color:#aaa}}
  td{{padding:7px 8px;border-bottom:1px solid #222}}
  tr:hover td{{background:#1a1a2e}}
  .btn{{padding:4px 10px;border:none;cursor:pointer;border-radius:3px;font-size:12px}}
  .btn-danger{{background:#c0392b;color:#fff}}
  .btn-warn{{background:#e67e22;color:#fff}}
  input[type=text],input[type=password]{{background:#1a1a2e;border:1px solid #444;color:#ddd;padding:8px;width:300px;border-radius:3px}}
  .card{{background:#1a1a2e;border-radius:6px;padding:20px;margin:10px;display:inline-block;min-width:180px;text-align:center}}
  .card .num{{font-size:36px;font-weight:bold;color:#e94560}}
  .card .lbl{{font-size:12px;color:#888;margin-top:4px}}
  .wrap{{padding:20px}}
  .flash{{background:#2c3e50;border-left:4px solid #e94560;padding:10px 16px;margin-bottom:16px;font-size:13px}}
  input[type=search]{{background:#1a1a2e;border:1px solid #444;color:#ddd;padding:7px;width:280px;border-radius:3px}}
</style>
</head><body>
{nav}
<div class="wrap">
{"<p class='flash'>" + breadcrumb + "</p>" if breadcrumb else ""}
{body}
</div>
</body></html>""")


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
async def login_page(error: str = ""):
    err_html = "<p style='color:#e94560'>Invalid password.</p>" if error else ""
    body = f"""
    <h2 style="color:#e94560">Admin Login</h2>
    {err_html}
    <form method="post" action="/login">
      <input type="password" name="password" placeholder="Admin API Key" autofocus><br><br>
      <button type="submit" class="btn btn-danger">Login</button>
    </form>"""
    return _page("Login", body)


@app.post("/login")
async def login_submit(response: Response, password: str = Form(...)):
    if not settings.admin_api_key or not secrets.compare_digest(password, settings.admin_api_key):
        return RedirectResponse("/login?error=1", status_code=302)
    token = secrets.token_urlsafe(32)
    _sessions.add(token)
    resp = RedirectResponse("/", status_code=302)
    resp.set_cookie(_SESSION_COOKIE, token, httponly=True, samesite="lax")
    return resp


@app.get("/logout")
async def logout(request: Request):
    token = request.cookies.get(_SESSION_COOKIE)
    if token:
        _sessions.discard(token)
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie(_SESSION_COOKIE)
    return resp


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    redir = _require_auth(request)
    if redir:
        return redir

    stats_repo = StatsRepository(admin_db)
    stats = await stats_repo.get_registry_stats()

    flag_repo = FlagRepository(admin_db)
    flags = await flag_repo.list_flags(limit=1000)
    flagged_count = len(flags)

    body = f"""
    <h2>Dashboard</h2>
    <div>
      <div class="card"><div class="num">{stats.total_agents}</div><div class="lbl">Total Agents</div></div>
      <div class="card"><div class="num">{stats.healthy_agents}</div><div class="lbl">Healthy Agents</div></div>
      <div class="card"><div class="num">{stats.health_percentage:.1f}%</div><div class="lbl">Health Rate</div></div>
      <div class="card"><div class="num">{flagged_count}</div><div class="lbl">Total Flags</div></div>
      <div class="card"><div class="num">{stats.new_agents_this_week}</div><div class="lbl">New (7d)</div></div>
      <div class="card"><div class="num">{stats.new_agents_this_month}</div><div class="lbl">New (30d)</div></div>
      <div class="card"><div class="num">{stats.avg_response_time_ms}ms</div><div class="lbl">Avg Response</div></div>
    </div>"""
    return _page("Dashboard", body)


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

@app.get("/flags", response_class=HTMLResponse)
async def list_flags(request: Request, msg: str = ""):
    redir = _require_auth(request)
    if redir:
        return redir

    flag_repo = FlagRepository(admin_db)
    flags = await flag_repo.list_flags(limit=500)

    rows = ""
    for f in flags:
        rows += f"""<tr>
          <td>{f.agent_name or "—"}</td>
          <td><small>{f.agent_id}</small></td>
          <td>{f.reason.value if f.reason else "—"}</td>
          <td style="max-width:300px;word-break:break-word">{f.details or "—"}</td>
          <td>{f.ip_address or "—"}</td>
          <td>{f.flagged_at.strftime("%Y-%m-%d %H:%M") if f.flagged_at else "—"}</td>
          <td>
            <form method="post" action="/agents/{f.agent_id}/ban" style="display:inline"
                  onsubmit="return confirm('Ban agent {f.agent_name or f.agent_id}?')">
              <button class="btn btn-danger" type="submit">Ban</button>
            </form>
          </td>
        </tr>"""

    body = f"""
    <h2>Flags <span style="font-size:14px;color:#888">({len(flags)} total)</span></h2>
    <table>
      <tr><th>Agent</th><th>ID</th><th>Reason</th><th>Details</th><th>Reporter IP</th><th>Date</th><th>Action</th></tr>
      {rows or "<tr><td colspan='7' style='text-align:center;color:#666'>No flags</td></tr>"}
    </table>"""
    return _page("Flags", body, breadcrumb=msg)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@app.get("/agents", response_class=HTMLResponse)
async def list_agents_page(request: Request, search: str = "", msg: str = ""):
    redir = _require_auth(request)
    if redir:
        return redir

    agent_repo = AgentRepository(admin_db)
    agents, total = await agent_repo.list_agents(search=search or None, limit=200)

    rows = ""
    for a in agents:
        conformance_label = "✓" if a.conformance else ("✗" if a.conformance is False else "?")
        hidden_badge = ' <span style="color:#e67e22">[hidden]</span>' if a.hidden else ""
        rows += f"""<tr>
          <td>{a.name}{hidden_badge}</td>
          <td>{a.author}</td>
          <td><a href="{a.wellKnownURI}" style="color:#7ec8e3" target="_blank" rel="noopener">{str(a.wellKnownURI)[:60]}</a></td>
          <td style="text-align:center">{conformance_label}</td>
          <td style="text-align:center">{a.flag_count}</td>
          <td>{a.created_at.strftime("%Y-%m-%d") if a.created_at else "—"}</td>
          <td>
            <form method="post" action="/agents/{a.id}/remove" style="display:inline"
                  onsubmit="return confirm('Remove {a.name}?')">
              <button class="btn btn-warn" type="submit">Remove</button>
            </form>
          </td>
        </tr>"""

    body = f"""
    <h2>Agents <span style="font-size:14px;color:#888">({total} total)</span></h2>
    <form method="get" style="margin-bottom:16px">
      <input type="search" name="search" value="{search}" placeholder="Search name / desc / author">
      <button type="submit" class="btn btn-warn" style="margin-left:8px">Search</button>
      {"<a href='/agents' style='margin-left:8px;color:#888;font-size:13px'>Clear</a>" if search else ""}
    </form>
    <table>
      <tr><th>Name</th><th>Author</th><th>Well-Known URI</th><th>Conf</th><th>Flags</th><th>Created</th><th>Action</th></tr>
      {rows or "<tr><td colspan='7' style='text-align:center;color:#666'>No agents</td></tr>"}
    </table>"""
    return _page("Agents", body, breadcrumb=msg)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

@app.post("/agents/{agent_id}/ban")
async def ban_agent(agent_id: UUID, request: Request):
    redir = _require_auth(request)
    if redir:
        return redir
    agent_repo = AgentRepository(admin_db)
    await agent_repo.delete(agent_id)
    return RedirectResponse(f"/flags?msg=Agent+{agent_id}+banned", status_code=302)


@app.post("/agents/{agent_id}/remove")
async def remove_agent(agent_id: UUID, request: Request):
    redir = _require_auth(request)
    if redir:
        return redir
    agent_repo = AgentRepository(admin_db)
    await agent_repo.delete(agent_id)
    return RedirectResponse(f"/agents?msg=Agent+{agent_id}+removed", status_code=302)
