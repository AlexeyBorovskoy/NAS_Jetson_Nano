#!/usr/bin/env python3
"""Validator for Sweden VPN v2 profiles (structural, policy, security, and native mihomo -t)."""

import argparse
import pathlib
import subprocess
import sys
import yaml


def check_cycles(groups_map):
    visiting = set()
    visited = set()

    def dfs(name):
        if name in visiting:
            raise ValueError(f"Cycle detected in proxy-groups at {name}")
        if name in visited or name not in groups_map:
            return
        visiting.add(name)
        for child in groups_map[name].get("proxies", []):
            dfs(child)
        visiting.remove(name)
        visited.add(name)

    for gname in groups_map:
        dfs(gname)


def validate_profile(path: pathlib.Path, mihomo_bin: pathlib.Path = None):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    errors = []

    if data.get("mode") != "rule":
        errors.append("mode must be 'rule'")

    proxies = data.get("proxies") or []
    proxy_names = [p.get("name") for p in proxies]
    if len(proxy_names) != len(set(proxy_names)):
        errors.append("Duplicate proxy names found")
    if "SE-PRIMARY" not in proxy_names or "SE-HY2" not in proxy_names:
        errors.append("Both SE-PRIMARY and SE-HY2 must exist")

    for p in proxies:
        if p.get("server") != "vpn.privet.dynv6.net" or p.get("port") != 443:
            errors.append(f"Unexpected endpoint in proxy {p.get('name')}")
        if p.get("type") == "hysteria2":
            if p.get("skip-cert-verify") is not False:
                errors.append("HY2 must explicitly set skip-cert-verify: false")
            if p.get("sni") != "vpn.privet.dynv6.net":
                errors.append("HY2 sni must be vpn.privet.dynv6.net")
        elif p.get("type") == "vless":
            if not p.get("tls"):
                errors.append("VLESS must have tls: true")
            if p.get("servername") != "www.googletagmanager.com":
                errors.append("VLESS REALITY servername must be www.googletagmanager.com")

    groups = data.get("proxy-groups") or []
    group_names = [g.get("name") for g in groups]
    if len(group_names) != len(set(group_names)):
        errors.append("Duplicate proxy-group names found")
    groups_map = {g["name"]: g for g in groups}
    valid_targets = set(proxy_names) | set(group_names) | {"DIRECT", "REJECT"}

    for g in groups:
        for member in g.get("proxies", []):
            if member not in valid_targets:
                errors.append(f"Broken reference '{member}' in group '{g['name']}'")

    try:
        check_cycles(groups_map)
    except ValueError as e:
        errors.append(str(e))

    auto_g = groups_map.get("AUTO")
    if not auto_g or auto_g.get("type") not in ("fallback", "url-test"):
        errors.append("AUTO group must exist with type fallback or url-test")
    elif "DIRECT" in auto_g.get("proxies", []):
        errors.append("AUTO group must NEVER contain DIRECT")

    dns = data.get("dns") or {}
    if not dns.get("enable"):
        errors.append("dns.enable must be true")
    for b in dns.get("default-nameserver", []):
        if b.startswith("https://"):
            errors.append(f"default-nameserver should not use DoH ({b}) to avoid bootstrap cycle")
    if not dns.get("proxy-server-nameserver"):
        errors.append("dns.proxy-server-nameserver must be set")

    rules = data.get("rules") or []
    if not rules or rules[-1] != "MATCH,PROXY":
        errors.append("Last rule must be MATCH,PROXY")

    if mihomo_bin and mihomo_bin.exists():
        res = subprocess.run([str(mihomo_bin), "-t", "-f", str(path)], capture_output=True, text=True)
        if res.returncode != 0:
            errors.append(f"mihomo -t failed: {res.stdout} {res.stderr}")

    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--releases-dir", default=".agent-work/private-releases/sweden-v2")
    ap.add_argument("--pattern", default="*-v*.yaml")
    ap.add_argument("--mihomo-bin", default=".agent-work/tmp/mihomo/mihomo.exe")
    args = ap.parse_args()

    rel_dir = pathlib.Path(args.releases_dir)
    mihomo_bin = pathlib.Path(args.mihomo_bin)
    yaml_files = sorted(rel_dir.rglob(args.pattern))
    if not yaml_files:
        print(f"ERROR: No *-v2.yaml files found under {rel_dir}", file=sys.stderr)
        sys.exit(2)

    all_ok = True
    for yf in yaml_files:
        errs = validate_profile(yf, mihomo_bin)
        if errs:
            all_ok = False
            print(f"FAIL {yf.name}: {errs}")
        else:
            print(f"PASS {yf.name}")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
