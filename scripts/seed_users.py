#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
BuzUp – User seeder.

Seeds the default system roles, creates a superuser and one user for every
system role (one account per user type). Idempotent: safe to re-run.

Runs against the dev stack by default (docker compose exec backend). With
--local it runs manage.py directly against the local virtualenv instead.

Usage:
    python scripts/seed_users.py [options]

Options:
    --local              Run manage.py locally (no Docker) using config.settings.dev
    --skip-roles         Skip seed_roles (roles must already exist)
    --skip-superuser     Skip superuser creation
    --skip-system-users  Skip creating one user per system role
    --no-color           Disable ANSI colour output
    --super-username     Superuser login name  (default: edircio)
    --super-email        Superuser e-mail      (default: edircio@buzup.co.mz)
    --super-password     Superuser password    (default: 123)
    --user-password      Password for per-role users (default: 123)
    --email-domain       E-mail domain for per-role users (default: buzup.dev)
    --compose-file       Override compose file (default: docker-compose.dev.yml)
"""

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Every system role the platform ships (see apps/core/permissions/base.py:DEFAULT_ROLES).
# 'admin' is the superuser; the remaining roles get one dedicated user each.
SYSTEM_ROLE_CODES = [
    "financial_manager",
    "operations_manager",
    "support",
    "pos_agent",
    "auditor",
]


# ─── colour helpers ────────────────────────────────────────────────────────────

class C:
    RESET = "\033[0m"; BOLD = "\033[1m"; BLUE = "\033[94m"; CYAN = "\033[96m"
    GREEN = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"; WHITE = "\033[97m"; GRAY = "\033[90m"

_use_color = True

def _c(text, *codes):
    return ("".join(codes) + str(text) + C.RESET) if _use_color else str(text)

def hdr(t):  print(f"\n  {_c('▶  ' + t, C.CYAN)}")
def ok(t):   print(f"     {_c('✔  ' + t, C.GREEN)}")
def warn(t): print(f"     {_c('⚠  ' + t, C.YELLOW)}")
def fail(t): print(f"     {_c('✖  ' + t, C.RED)}")
def info(t): print(f"     {_c('•  ' + t, C.WHITE)}")
def dim(t):  print(f"        {_c(t, C.GRAY)}")


# ─── execution backends ────────────────────────────────────────────────────────

_LOCAL = False
_COMPOSE_FILE = "docker-compose.dev.yml"

def _compose_path():
    return os.path.join(ROOT, _COMPOSE_FILE)

def manage_exec(manage_args):
    """Run `manage.py <args>`, return (rc, output)."""
    if _LOCAL:
        cmd = (f'python backend/manage.py {manage_args} '
               f'--settings=config.settings.dev')
    else:
        cmd = (f'docker compose -f "{_compose_path()}" exec -T '
               f'backend python manage.py {manage_args}')
    r = subprocess.run(cmd, shell=True, cwd=ROOT,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout

def manage_exec_env(env_pairs, manage_args):
    """Run manage.py with extra env vars (used for createsuperuser --noinput)."""
    if _LOCAL:
        prefix = " ".join(f'{k}={v}' for k, v in env_pairs.items())
        cmd = (f'{prefix} python backend/manage.py {manage_args} '
               f'--settings=config.settings.dev')
    else:
        envflags = " ".join(f'-e {k}={v}' for k, v in env_pairs.items())
        cmd = (f'docker compose -f "{_compose_path()}" exec -T {envflags} '
               f'backend python manage.py {manage_args}')
    r = subprocess.run(cmd, shell=True, cwd=ROOT,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout

def shell_exec(python_script):
    """Pipe a python script into manage.py shell, return (rc, output)."""
    if _LOCAL:
        cmd = ('python backend/manage.py shell --settings=config.settings.dev')
    else:
        cmd = (f'docker compose -f "{_compose_path()}" exec -T '
               f'backend python manage.py shell')
    r = subprocess.run(cmd, shell=True, cwd=ROOT, input=python_script,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout


# ─── steps ─────────────────────────────────────────────────────────────────────

def seed_roles():
    rc, out = manage_exec("seed_roles")
    if rc == 0:
        ok("seed_roles completed")
        for line in out.strip().splitlines():
            if line.strip():
                dim(line.strip())
        return True
    fail("seed_roles failed")
    for line in out.strip().splitlines()[-6:]:
        dim(line)
    return False


def superuser_exists(username):
    script = f"""
from django.contrib.auth import get_user_model
User = get_user_model()
print("EXISTS:True" if User.objects.filter(username="{username}").exists() else "EXISTS:False")
"""
    _, out = shell_exec(script)
    return "EXISTS:True" in out


def create_superuser(username, email, password):
    if superuser_exists(username):
        ok(f"Superuser '{username}' already exists")
        return True
    rc, out = manage_exec_env(
        {
            "DJANGO_SUPERUSER_USERNAME": username,
            "DJANGO_SUPERUSER_EMAIL": email,
            "DJANGO_SUPERUSER_PASSWORD": password,
        },
        "createsuperuser --noinput",
    )
    if rc == 0:
        ok(f"Superuser '{username}' created  ({email})")
        return True
    fail("createsuperuser failed")
    for line in out.strip().splitlines()[-4:]:
        dim(line)
    return False


def create_system_users(password, email_domain):
    """One user per system role, linked to its global Role via UserRole. Idempotent."""
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
    rc, out = shell_exec(script)
    created = []
    existing = []
    for code, username, state in re.findall(r"USER:([^\n:]+):([^\n:]+):([A-Z]+)", out):
        (created if state == "CREATED" else existing).append((code, username))
    missing = re.findall(r"NOROLE:([^\n]+)", out)
    for code, username in created:
        ok(f"Created {code} → {username}")
    for code, username in existing:
        info(f"{code} already exists → {username}")
    for code in missing:
        warn(f"Role {code} not found — run seed_roles first (skipped)")
    if rc != 0 and not created and not existing:
        fail("system user creation failed")
        for line in out.strip().splitlines()[-6:]:
            dim(line)
        return False
    return not missing


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    global _use_color, _LOCAL, _COMPOSE_FILE

    parser = argparse.ArgumentParser(
        description="BuzUp user seeder",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--local",             action="store_true")
    parser.add_argument("--skip-roles",        action="store_true")
    parser.add_argument("--skip-superuser",    action="store_true")
    parser.add_argument("--skip-system-users", action="store_true")
    parser.add_argument("--no-color",          action="store_true")
    parser.add_argument("--super-username",  default="edircio")
    parser.add_argument("--super-email",     default="edircio@buzup.co.mz")
    parser.add_argument("--super-password",  default="123")
    parser.add_argument("--user-password",   default="123")
    parser.add_argument("--email-domain",    default="buzup.dev")
    parser.add_argument("--compose-file",    default="docker-compose.dev.yml")
    args = parser.parse_args()

    _use_color = not args.no_color and sys.stdout.isatty()
    _LOCAL = args.local
    _COMPOSE_FILE = args.compose_file

    print()
    print(_c("  ╔════════════════════════════════════════════════════════╗", C.BLUE, C.BOLD))
    print(_c("  ║                BuzUp — User Seeder                     ║", C.BLUE, C.BOLD))
    print(_c("  ╚════════════════════════════════════════════════════════╝", C.BLUE, C.BOLD))
    print(_c(f"  mode: {'local venv' if _LOCAL else 'docker (' + _COMPOSE_FILE + ')'}", C.GRAY))

    errors = []

    if not args.skip_roles:
        hdr("System roles")
        if not seed_roles():
            errors.append("seed_roles failed")
    else:
        warn("Roles skipped (--skip-roles)")

    if not args.skip_superuser:
        hdr("Superuser")
        if not create_superuser(args.super_username, args.super_email, args.super_password):
            errors.append("superuser failed")
    else:
        warn("Superuser skipped (--skip-superuser)")

    if not args.skip_system_users:
        hdr("System role users")
        info("One user per role: " + ", ".join(SYSTEM_ROLE_CODES))
        if not create_system_users(args.user_password, args.email_domain):
            errors.append("system users incomplete")
    else:
        warn("System users skipped (--skip-system-users)")

    print()
    if errors:
        fail(f"Done with {len(errors)} error(s): " + "; ".join(errors))
        sys.exit(1)
    ok("All users seeded successfully")
    print()
    print(_c("  Credentials (dev):", C.CYAN))
    dim(f"superuser:  {args.super_username} / {args.super_password}")
    for code in SYSTEM_ROLE_CODES:
        dim(f"{code:<20} {code}@{args.email_domain} / {args.user_password}")
    print()


if __name__ == "__main__":
    main()
