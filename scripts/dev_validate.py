#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
BuzUp – Dev environment validator.

Starts the dev stack, waits for readiness, runs checks/tests,
seeds the default system roles, creates a superuser and one user for
every system role, then prints a detailed summary.

Usage:
    python scripts/dev_validate.py [options]

Options:
    --no-build           Skip --build on docker compose up (faster restart)
    --skip-tests         Skip Django test suite
    --skip-superuser     Skip superuser creation
    --skip-system-users  Skip creating one user per system role
    --skip-seed          Skip seed_roles
    --no-color           Disable ANSI colour output
    --super-username     Superuser login name  (default: edircio)
    --super-email        Superuser e-mail      (default: edircio@buzup.co.mz)
    --super-password     Superuser password    (default: 123)
    --user-password      Password for the per-role users (default: 123)
    --health-timeout     Seconds to wait for backend readiness (default: 90)
    --compose-file       Override compose file (default: docker-compose.dev.yml)
"""

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEV_PORT_DEFAULTS = {
    "POSTGRES_PORT":  "5436",
    "REDIS_PORT":     "6383",
    "BACKEND_PORT":   "8008",
    "FRONTEND_PORT":  "3008",
}

# Every system role the platform ships (see apps/core/permissions/base.py:DEFAULT_ROLES).
# 'admin' is covered by the superuser, so the validator creates one user for each of
# the remaining roles so that every non-admin user type exists in dev.
SYSTEM_ROLE_CODES = [
    "financial_manager",
    "operations_manager",
    "support",
    "pos_agent",
    "auditor",
]


# ─── colour helpers ────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    WHITE  = "\033[97m"
    GRAY   = "\033[90m"

_use_color = True

def _c(text, *codes):
    if not _use_color:
        return str(text)
    return "".join(codes) + str(text) + C.RESET

def hdr(t):  print(f"\n  {_c('▶  ' + t, C.CYAN)}")
def ok(t):   print(f"     {_c('✔  ' + t, C.GREEN)}")
def warn(t): print(f"     {_c('⚠  ' + t, C.YELLOW)}")
def fail(t): print(f"     {_c('✖  ' + t, C.RED)}")
def info(t): print(f"     {_c('•  ' + t, C.WHITE)}")
def dim(t):  print(f"        {_c(t, C.GRAY)}")
def sep():   print(f"  {_c('─' * 56, C.GRAY)}")


# ─── subprocess helpers ────────────────────────────────────────────────────────

def _compose_file():
    return os.environ.get("COMPOSE_FILE", "docker-compose.dev.yml")

def _compose_path():
    return os.path.join(ROOT, _compose_file())

def capture(cmd):
    r = subprocess.run(
        cmd, shell=True, cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    return r.returncode, r.stdout

def compose_run(args_str):
    cmd = f'docker compose -f "{_compose_path()}" {args_str}'
    r = subprocess.run(cmd, shell=True, cwd=ROOT)
    return r.returncode

def backend_exec(sh_cmd):
    cmd = f'docker compose -f "{_compose_path()}" exec -T backend sh -c "{sh_cmd}"'
    r = subprocess.run(
        cmd, shell=True, cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    return r.returncode, r.stdout

def backend_shell(python_script):
    cmd = f'docker compose -f "{_compose_path()}" exec -T backend python manage.py shell'
    r = subprocess.run(
        cmd, shell=True, cwd=ROOT,
        input=python_script,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    return r.returncode, r.stdout


# ─── readiness ────────────────────────────────────────────────────────────────

def wait_for_backend(backend_url, max_attempts, interval=3):
    import urllib.request

    url = f"{backend_url}/api/health/"
    for attempt in range(1, max_attempts + 1):
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except Exception:
            if attempt >= max_attempts:
                return False
            print(f"        {_c(f'… {attempt * interval}s — waiting for backend…', C.GRAY)}")
            time.sleep(interval)
    return False


# ─── parsers ──────────────────────────────────────────────────────────────────

def parse_migrations(output):
    per_app = {}
    current_app = None
    for line in output.splitlines():
        if line and not line.startswith(" ") and not line.startswith("\t"):
            current_app = line.strip()
            per_app[current_app] = {"applied": 0, "pending": 0}
        elif current_app:
            if "[X]" in line:
                per_app[current_app]["applied"] += 1
            elif "[ ]" in line:
                per_app[current_app]["pending"] += 1

    total_applied = sum(v["applied"] for v in per_app.values())
    total_pending = sum(v["pending"] for v in per_app.values())
    return total_applied, total_pending, per_app


def parse_test_output(output):
    ran_m    = re.search(r"Ran (\d+) tests? in ([\d.]+)s", output)
    ok_m     = re.search(r"^OK$", output, re.MULTILINE)
    fail_m   = re.search(r"^FAILED \((.+)\)$", output, re.MULTILINE)
    error_m  = re.search(r"^ERROR$", output, re.MULTILINE)
    skip_m   = re.search(r"skipped=(\d+)", output)
    err_cnt  = re.search(r"errors=(\d+)", output)
    fail_cnt = re.search(r"failures=(\d+)", output)

    return {
        "ran":      int(ran_m.group(1)) if ran_m else 0,
        "duration": (ran_m.group(2) + "s") if ran_m else "?",
        "status":   ("PASSED" if ok_m
                     else "FAILED" if fail_m
                     else "ERROR"  if error_m
                     else "UNKNOWN"),
        "detail":    fail_m.group(1) if fail_m else "",
        "skipped":   int(skip_m.group(1))  if skip_m  else 0,
        "errors":    int(err_cnt.group(1)) if err_cnt else 0,
        "failures":  int(fail_cnt.group(1)) if fail_cnt else 0,
    }


def gather_user_stats():
    script = """
from django.contrib.auth import get_user_model
User = get_user_model()
total = User.objects.count()
supers = list(User.objects.filter(is_superuser=True).values_list('username', 'email'))
regular = User.objects.filter(is_superuser=False).count()
active = User.objects.filter(is_active=True).count()
print(f"TOTAL:{total}")
print(f"ACTIVE:{active}")
print(f"REGULAR:{regular}")
for u, e in supers:
    print(f"SUPER:{u}:{e}")
"""
    rc, out = backend_shell(script)
    total_m   = re.search(r"TOTAL:(\d+)", out)
    active_m  = re.search(r"ACTIVE:(\d+)", out)
    regular_m = re.search(r"REGULAR:(\d+)", out)
    supers    = re.findall(r"SUPER:([^\n:]+):([^\n]*)", out)
    return {
        "total":   int(total_m.group(1))   if total_m   else "?",
        "active":  int(active_m.group(1))  if active_m  else "?",
        "regular": int(regular_m.group(1)) if regular_m else "?",
        "supers":  supers,
    }


def create_system_users(password, email_domain="buzup.dev"):
    """Create one user per system role, each linked to the matching global Role via
    a UserRole assignment. Idempotent (get_or_create)."""
    roles_py = repr(SYSTEM_ROLE_CODES)
    script = f"""
from django.contrib.auth import get_user_model
from apps.users.models import Role, UserRole
User = get_user_model()
PASSWORD = {password!r}
DOMAIN = {email_domain!r}
ROLES = {roles_py}
for code in ROLES:
    role = Role.objects.filter(code=code).first()
    if not role:
        print("NOROLE:" + code)
        continue
    username = code
    email = username + "@" + DOMAIN
    user, created = User.objects.get_or_create(
        username=username,
        defaults={{"email": email, "is_active": True, "is_staff": True}},
    )
    if created:
        user.set_password(PASSWORD)
        user.email = email
        user.is_active = True
        user.is_staff = True
        user.save()
    UserRole.objects.get_or_create(user=user, role=role)
    print("USER:" + code + ":" + username + ":" + ("CREATED" if created else "EXISTS"))
"""
    rc, out = backend_shell(script)
    result = {"created": [], "existing": [], "missing_roles": [], "status": "done"}
    for code, username, state in re.findall(r"USER:([^\n:]+):([^\n:]+):([A-Z]+)", out):
        (result["created"] if state == "CREATED" else result["existing"]).append((code, username))
    result["missing_roles"] = re.findall(r"NOROLE:([^\n]+)", out)
    if rc != 0 and not result["created"] and not result["existing"]:
        result["status"] = "FAILED"
    return result, out


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    global _use_color

    parser = argparse.ArgumentParser(
        description="BuzUp dev environment validator",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--no-build",          action="store_true")
    parser.add_argument("--skip-tests",        action="store_true")
    parser.add_argument("--skip-superuser",    action="store_true")
    parser.add_argument("--skip-system-users", action="store_true")
    parser.add_argument("--skip-seed",         action="store_true")
    parser.add_argument("--no-color",        action="store_true")
    parser.add_argument("--super-username",  default="edircio")
    parser.add_argument("--super-email",     default="edircio@buzup.co.mz")
    parser.add_argument("--super-password",  default="123")
    parser.add_argument("--user-password",   default="123")
    parser.add_argument("--health-timeout",  type=int, default=90)
    parser.add_argument("--compose-file",    default="docker-compose.dev.yml")
    args = parser.parse_args()

    _use_color = not args.no_color and sys.stdout.isatty()

    os.environ["COMPOSE_FILE"] = args.compose_file
    for k, v in DEV_PORT_DEFAULTS.items():
        os.environ.setdefault(k, v)

    backend_url = f"http://localhost:{os.environ['BACKEND_PORT']}"
    start = datetime.now()

    R = {
        "docker_ok":       False,
        "stack_started":   False,
        "backend_ready":   False,
        "migr_applied":    0,
        "migr_pending":    0,
        "migr_per_app":    {},
        "migr_status":     "",
        "check_ok":        False,
        "test":            {"status": "skipped", "ran": 0, "duration": "", "detail": "",
                            "skipped": 0, "errors": 0, "failures": 0},
        "super_status":    "skipped",
        "super_details":   "",
        "users":           {"total": "?", "active": "?", "regular": "?", "supers": []},
        "system_users":    {"status": "skipped", "created": [], "existing": [], "missing_roles": []},
        "seed_status":     "skipped",
        "container_lines": [],
        "errors":          [],
    }

    # ── BANNER ────────────────────────────────────────────────────────────────
    print()
    print(_c("  ╔════════════════════════════════════════════════════════╗", C.BLUE, C.BOLD))
    print(_c("  ║          BuzUp — Dev Environment Validator             ║", C.BLUE, C.BOLD))
    print(_c("  ╚════════════════════════════════════════════════════════╝", C.BLUE, C.BOLD))
    print(_c(f"  {start.strftime('%Y-%m-%d %H:%M:%S')}   compose: {args.compose_file}", C.GRAY))
    print()

    # ── 1. PREREQUISITES ──────────────────────────────────────────────────────
    hdr("Prerequisites")

    rc, _ = capture("docker info")
    if rc != 0:
        fail("Docker daemon not running. Start Docker Desktop first.")
        sys.exit(1)
    ok("Docker daemon running")

    if not os.path.exists(_compose_path()):
        fail(f"{args.compose_file} not found at {_compose_path()}")
        sys.exit(1)
    ok(f"{args.compose_file} found")
    R["docker_ok"] = True

    # ── 2. START STACK ────────────────────────────────────────────────────────
    hdr("Starting dev stack")

    up_flags = "up -d" + ("" if args.no_build else " --build")
    info(f"docker compose {up_flags}")

    rc = compose_run(up_flags)
    if rc != 0:
        fail(f"docker compose up failed (exit {rc})")
        R["errors"].append("docker compose up failed")
        sys.exit(1)
    ok("All containers started")
    R["stack_started"] = True

    # ── 3. WAIT FOR BACKEND ───────────────────────────────────────────────────
    max_att = max(1, args.health_timeout // 3)
    hdr(f"Waiting for backend  (timeout: {args.health_timeout}s)")
    info(f"GET {backend_url}/api/health/")

    if wait_for_backend(backend_url, max_attempts=max_att, interval=3):
        ok("Backend ready")
        R["backend_ready"] = True
    else:
        fail(f"Backend not ready after {args.health_timeout}s")
        compose_run("logs --tail=80 backend")
        R["errors"].append(f"Backend health check timed out ({args.health_timeout}s)")

    # ── 4. DJANGO SYSTEM CHECK ────────────────────────────────────────────────
    hdr("Django system check")

    rc, check_out = backend_exec("python manage.py check 2>&1")
    if rc == 0:
        ok("System check passed — no issues")
        R["check_ok"] = True
    else:
        warn("System check reported issues:")
        for line in check_out.strip().splitlines()[-8:]:
            dim(line)
        R["errors"].append("manage.py check failed")

    # ── 5. MIGRATION STATUS ───────────────────────────────────────────────────
    hdr("Migration status")

    rc, migr_raw = backend_exec("python manage.py showmigrations --list 2>&1")
    applied, pending, per_app = parse_migrations(migr_raw)
    R["migr_per_app"] = per_app

    if pending > 0:
        warn(f"{applied} applied, {pending} pending — running migrate…")
        rc2, _ = backend_exec("python manage.py migrate --noinput 2>&1")
        if rc2 == 0:
            ok(f"Migrations applied ({pending} new)")
            R["migr_applied"] = applied + pending
            R["migr_pending"] = 0
            R["migr_status"]  = f"{applied + pending} applied (ran {pending} new)"
        else:
            fail("migrate failed")
            R["errors"].append("python manage.py migrate failed")
            R["migr_status"] = "FAILED"
    else:
        ok(f"{applied} migrations applied, 0 pending")
        R["migr_applied"] = applied
        R["migr_pending"] = 0
        R["migr_status"]  = f"{applied} applied, 0 pending"

    # ── 6. TESTS ──────────────────────────────────────────────────────────────
    if not args.skip_tests:
        hdr("Running test suite")
        info("python manage.py test apps --verbosity=2")
        print()

        rc, test_raw = backend_exec("TESTING=True python manage.py test apps --verbosity=2 2>&1")

        for line in test_raw.splitlines():
            dim(line)
        print()

        tr = parse_test_output(test_raw)
        tr["rc"] = rc
        R["test"] = tr

        if tr["status"] == "PASSED":
            ok(f"Tests PASSED — {tr['ran']} test(s) in {tr['duration']}")
        elif tr["status"] in ("FAILED", "ERROR"):
            fail(f"Tests {tr['status']} — {tr['detail']}")
            R["errors"].append(f"Test suite {tr['status']}: {tr['detail']}")
        else:
            warn("Could not determine test outcome — check output above")
    else:
        warn("Tests skipped (--skip-tests)")

    # ── 7. SEED ROLES ─────────────────────────────────────────────────────────
    # Roles must exist before per-role users can be attached.
    if not args.skip_seed:
        hdr("Seeding system roles")
        info("python manage.py seed_roles")
        rc, seed_out = backend_exec("python manage.py seed_roles 2>&1")
        if rc == 0:
            ok("seed_roles completed")
            R["seed_status"] = "done"
        else:
            warn("seed_roles exited non-zero")
            for line in seed_out.strip().splitlines()[-6:]:
                dim(line)
            R["seed_status"] = "FAILED"
            R["errors"].append("seed_roles failed")
    else:
        warn("Seed skipped (--skip-seed)")

    # ── 8. SUPERUSER ──────────────────────────────────────────────────────────
    if not args.skip_superuser:
        hdr("Superuser")

        check_script = f"""
from django.contrib.auth import get_user_model
User = get_user_model()
exists = User.objects.filter(username="{args.super_username}").exists()
print("EXISTS:True" if exists else "EXISTS:False")
"""
        _, exists_out = backend_shell(check_script)
        exists = "EXISTS:True" in exists_out

        if exists:
            ok(f"Superuser '{args.super_username}' already exists")
            R["super_status"]  = "already exists"
            R["super_details"] = args.super_username
        else:
            info(f"Creating superuser '{args.super_username}'…")
            create_cmd = (
                f'docker compose -f "{_compose_path()}" exec -T '
                f'-e DJANGO_SUPERUSER_USERNAME={args.super_username} '
                f'-e DJANGO_SUPERUSER_EMAIL={args.super_email} '
                f'-e DJANGO_SUPERUSER_PASSWORD={args.super_password} '
                f'backend python manage.py createsuperuser --noinput 2>&1'
            )
            r = subprocess.run(
                create_cmd, shell=True, cwd=ROOT,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            if r.returncode == 0:
                ok(f"Superuser '{args.super_username}' created  ({args.super_email})")
                R["super_status"]  = "created"
                R["super_details"] = f"{args.super_username} / {args.super_email}"
            else:
                fail("createsuperuser failed")
                for line in r.stdout.strip().splitlines()[-4:]:
                    dim(line)
                R["errors"].append(f"createsuperuser failed for '{args.super_username}'")
                R["super_status"] = "FAILED"
    else:
        warn("Superuser step skipped (--skip-superuser)")

    # ── 9. USER STATS ─────────────────────────────────────────────────────────
    R["users"] = gather_user_stats()

    # ── 10. SYSTEM USER TYPES ─────────────────────────────────────────────────
    if not args.skip_system_users:
        hdr("System user types")
        info("Creating one user per role: " + ", ".join(SYSTEM_ROLE_CODES))
        su, _su_raw = create_system_users(args.user_password)
        R["system_users"] = {
            "status":        su["status"],
            "created":       su["created"],
            "existing":      su["existing"],
            "missing_roles": su["missing_roles"],
        }
        if su["status"] == "FAILED":
            fail("Failed to create system users")
            for line in _su_raw.strip().splitlines()[-6:]:
                dim(line)
            R["errors"].append("system user creation failed")
        else:
            for code, username in su["created"]:
                ok(f"Created {code} → {username}")
            for code, username in su["existing"]:
                info(f"{code} already exists → {username}")
            for code in su["missing_roles"]:
                warn(f"Role {code} not found — run seed_roles first (skipped)")
            if su["missing_roles"]:
                R["errors"].append("system users: missing roles " + ", ".join(su["missing_roles"]))
        # Refresh user stats so the summary reflects the new accounts.
        R["users"] = gather_user_stats()
    else:
        warn("System users skipped (--skip-system-users)")

    # ── 11. CONTAINER STATUS ──────────────────────────────────────────────────
    rc, ps_out = capture(
        f'docker compose -f "{_compose_path()}" '
        'ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"'
    )
    R["container_lines"] = ps_out.strip().splitlines()

    # ══════════════════════════════════════════════════════════════════════════
    #  SUMMARY
    # ══════════════════════════════════════════════════════════════════════════
    elapsed = int((datetime.now() - start).total_seconds())

    print()
    print(_c("  ╔════════════════════════════════════════════════════════╗", C.BLUE, C.BOLD))
    print(_c("  ║           SUMMARY  —  Dev Environment (BuzUp)          ║", C.BLUE, C.BOLD))
    print(_c("  ╚════════════════════════════════════════════════════════╝", C.BLUE, C.BOLD))
    print()

    # ── Docker containers ─────────────────────────────────────────────────────
    print(_c("  DOCKER CONTAINERS", C.CYAN))
    sep()
    if R["container_lines"]:
        for line in R["container_lines"]:
            color = C.GREEN if "running" in line.lower() else (
                    C.RED   if "exit"    in line.lower() else C.WHITE)
            print(f"  {_c(line, color)}")
    else:
        print(f"  {_c('(no container info)', C.GRAY)}")
    print()

    # ── Configuration ─────────────────────────────────────────────────────────
    print(_c("  CONFIGURATION", C.CYAN))
    sep()
    print(f"  {'Compose file:':<30} {args.compose_file}")
    print(f"  {'Django settings:':<30} config.settings.dev")
    print(f"  {'Backend port (host):':<30} {os.environ['BACKEND_PORT']}")
    print(f"  {'Postgres port (host):':<30} {os.environ['POSTGRES_PORT']} → db:5432")
    print(f"  {'Redis port (host):':<30} {os.environ['REDIS_PORT']} → redis:6379")
    print(f"  {'Frontend (host):':<30} {os.environ['FRONTEND_PORT']}")
    print()

    # ── Database ──────────────────────────────────────────────────────────────
    print(_c("  DATABASE  /  MIGRATIONS", C.CYAN))
    sep()
    mc = C.GREEN if R["migr_status"] and "FAILED" not in R["migr_status"] else C.RED
    print(f"  {'Engine:':<30} PostgreSQL 16-alpine")
    print(f"  {'Overall status:':<30} {_c(R['migr_status'], mc)}")
    if R["migr_per_app"]:
        print(f"  {'Per-app breakdown:':<30}")
        for app, counts in sorted(R["migr_per_app"].items()):
            a, p = counts["applied"], counts["pending"]
            status_str = f"{a} applied" + (f", {_c(str(p) + ' pending', C.YELLOW)}" if p else "")
            print(f"    {'  ' + app:<28} {status_str}")
    print()

    # ── Users ─────────────────────────────────────────────────────────────────
    print(_c("  USERS", C.CYAN))
    sep()
    u = R["users"]
    print(f"  {'Total users:':<30} {u['total']}")
    print(f"  {'  Active:':<30} {u['active']}")
    print(f"  {'  Regular (non-super):':<30} {u['regular']}")
    print(f"  {'Superuser step:':<30} {R['super_status']}")
    if R["super_details"]:
        print(_c(f"  {'  Details:':<30} {R['super_details']}", C.GRAY))
    if u["supers"]:
        print(f"  {'Superuser accounts:':<30}")
        for uname, email in u["supers"]:
            print(f"    {_c('  ' + uname, C.WHITE):<30} {_c(email, C.GRAY)}")
    else:
        print(f"  {'Superuser accounts:':<30} {_c('(none)', C.GRAY)}")
    print()

    # ── System role users ─────────────────────────────────────────────────────
    print(_c("  SYSTEM ROLE USERS", C.CYAN))
    sep()
    suR = R["system_users"]
    su_st = suR["status"]
    su_color = (C.GREEN if su_st == "done"
                else C.RED if su_st == "FAILED"
                else C.YELLOW)
    print(f"  {'Status:':<30} {_c(su_st, su_color)}")
    if suR["created"] or suR["existing"]:
        print(f"  {'Accounts (one per role):':<30}")
        for code, username in suR["created"]:
            print(f"    {_c('+ ' + code, C.GREEN):<30} {_c(username, C.GRAY)}")
        for code, username in suR["existing"]:
            print(f"    {_c('= ' + code, C.WHITE):<30} {_c(username, C.GRAY)}")
    if suR["missing_roles"]:
        print(f"  {'Missing roles:':<30} {_c(', '.join(suR['missing_roles']), C.YELLOW)}")
    print()

    # ── Tests ─────────────────────────────────────────────────────────────────
    print(_c("  TEST SUITE", C.CYAN))
    sep()
    ts = R["test"]["status"]
    tc = (C.GREEN  if ts == "PASSED"
          else C.RED    if ts in ("FAILED", "ERROR")
          else C.YELLOW)
    print(f"  {'Status:':<30} {_c(ts, tc)}")
    if R["test"]["ran"]:
        print(f"  {'Tests run:':<30} {R['test']['ran']}")
        print(f"  {'Duration:':<30} {R['test']['duration']}")
        if R["test"]["failures"]:
            print(f"  {'Failures:':<30} {_c(str(R['test']['failures']), C.RED)}")
        if R["test"]["errors"]:
            print(f"  {'Errors:':<30} {_c(str(R['test']['errors']), C.RED)}")
        if R["test"]["skipped"]:
            print(f"  {'Skipped:':<30} {_c(str(R['test']['skipped']), C.YELLOW)}")
    if R["test"].get("detail"):
        print(f"  {'Failure detail:':<30} {_c(R['test']['detail'], C.RED)}")
    print()

    # ── Seed ──────────────────────────────────────────────────────────────────
    print(_c("  SEED & ROLES", C.CYAN))
    sep()
    sc = (C.GREEN  if R["seed_status"] == "done"
          else C.RED    if R["seed_status"] == "FAILED"
          else C.YELLOW)
    print(f"  {'seed_roles:':<30} {_c(R['seed_status'], sc)}")
    print()

    # ── Access URLs ───────────────────────────────────────────────────────────
    api = os.environ["BACKEND_PORT"]
    pub = os.environ["FRONTEND_PORT"]

    print(_c("  ACCESS URLS", C.CYAN))
    sep()
    print(f"  {'Frontend (Vite dev):':<30} {_c('http://localhost:' + pub, C.CYAN)}")
    print(f"  {'API root:':<30} {_c('http://localhost:' + api + '/api/', C.CYAN)}")
    print(f"  {'Health check:':<30} {_c('http://localhost:' + api + '/api/health/', C.CYAN)}")
    print(f"  {'Django admin:':<30} {_c('http://localhost:' + api + '/admin/', C.CYAN)}")
    print(f"  {'Swagger UI:':<30} {_c('http://localhost:' + api + '/api/docs/', C.CYAN)}")
    print(f"  {'OpenAPI schema:':<30} {_c('http://localhost:' + api + '/api/schema/', C.CYAN)}")
    print()

    # ── Errors ────────────────────────────────────────────────────────────────
    if R["errors"]:
        print(_c(f"  ERRORS  ({len(R['errors'])})", C.RED, C.BOLD))
        sep()
        for msg in R["errors"]:
            print(_c(f"  ✖  {msg}", C.RED))
        print()

    # ── Footer ────────────────────────────────────────────────────────────────
    sep()
    ok_count  = sum([
        R["docker_ok"], R["stack_started"], R["backend_ready"], R["check_ok"],
        R["test"]["status"] == "PASSED",
        R["seed_status"] == "done",
        R["super_status"] in ("created", "already exists"),
        R["system_users"]["status"] == "done",
    ])
    total_checks = 8
    status_str   = "ALL OK" if not R["errors"] else f"{len(R['errors'])} ERROR(S)"
    status_color = C.GREEN if not R["errors"] else C.RED
    print(
        _c(f"  Status: {status_str:<24} Checks OK: {ok_count}/{total_checks}   Time: {elapsed}s", status_color)
    )
    sep()
    print()

    # ── Quick-reference commands ──────────────────────────────────────────────
    cf = args.compose_file
    print(_c("  QUICK COMMANDS", C.GRAY))
    print(_c(f"  Logs all:   docker compose -f {cf} logs -f", C.GRAY))
    print(_c(f"  Logs back:  docker compose -f {cf} logs -f backend", C.GRAY))
    print(_c(f"  Stop:       docker compose -f {cf} down", C.GRAY))
    print(_c(f"  Shell:      docker compose -f {cf} exec backend python manage.py shell", C.GRAY))
    print(_c(f"  Re-seed:    docker compose -f {cf} exec backend python manage.py seed_roles", C.GRAY))
    print(_c(f"  Users:      python scripts/seed_users.py", C.GRAY))
    print(_c(f"  Tests:      docker compose -f {cf} exec backend python manage.py test apps -v2", C.GRAY))
    print(_c(f"  Migrations: docker compose -f {cf} exec backend python manage.py migrate", C.GRAY))
    print()

    sys.exit(int(bool(R["errors"])))


if __name__ == "__main__":
    main()
