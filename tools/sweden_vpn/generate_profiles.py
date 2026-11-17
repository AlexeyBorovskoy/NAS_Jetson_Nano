#!/usr/bin/env python3
"""Reproducible profile generator for Sweden VPN (v2 and v3).

Reads anonymized inventory + policy template + private secrets source,
writes per-device YAML profiles into private-releases (outside Git),
and writes a secret-free release manifest into releases/<version>/manifest.json.
"""

import argparse
import copy
import hashlib
import json
import os
import pathlib
import secrets
import sys
import time
import uuid
import yaml


def extract_device_credentials(v1_path: pathlib.Path):
    if not v1_path.exists():
        raise FileNotFoundError(f"Missing credentials source file: {v1_path}")
    data = yaml.safe_load(v1_path.read_text(encoding="utf-8"))
    proxies = {p.get("type"): p for p in data.get("proxies", [])}
    hy2 = proxies.get("hysteria2")
    vless = proxies.get("vless")
    if not hy2 or not hy2.get("password"):
        raise ValueError(f"Missing hysteria2 credentials in {v1_path}")
    if not vless or not vless.get("uuid"):
        raise ValueError(f"Missing vless credentials in {v1_path}")
    reality_opts = vless.get("reality-opts") or {}
    if not reality_opts.get("public-key") or not reality_opts.get("short-id"):
        raise ValueError(f"Missing reality-opts in {v1_path}")

    extra_cidrs = [
        r for r in data.get("rules", [])
        if r.startswith("IP-CIDR,")
        and not r.startswith(("IP-CIDR,192.168.", "IP-CIDR,10.", "IP-CIDR,172.16."))
    ]
    return {
        "hy2_password": hy2["password"],
        "vless_uuid": vless["uuid"],
        "reality_public_key": reality_opts["public-key"],
        "reality_short_id": reality_opts["short-id"],
        "extra_cidrs": extra_cidrs,
    }


def collect_old_secrets(inv: dict, secrets_dir: pathlib.Path):
    old_uuids = set()
    old_passwords = set()
    ref_reality = None
    ref_cidrs_by_dev = {}
    for dev in inv["devices"]:
        if dev.get("v1_file"):
            c = extract_device_credentials(secrets_dir / dev["v1_file"])
            old_uuids.add(c["vless_uuid"])
            old_passwords.add(c["hy2_password"])
            ref_reality = (c["reality_public_key"], c["reality_short_id"])
            if c["extra_cidrs"]:
                ref_cidrs_by_dev[dev["device_id"]] = c["extra_cidrs"]
    if not ref_reality:
        raise RuntimeError("Could not extract reference REALITY public_key/short_id from v1 files")
    return old_uuids, old_passwords, ref_reality, ref_cidrs_by_dev


def load_or_create_v3_vault(vault_path: pathlib.Path, inv: dict, old_uuids: set, old_passwords: set):
    if vault_path.exists():
        vault = json.loads(vault_path.read_text(encoding="utf-8"))
    else:
        vault = {"schema_version": "3.0", "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "credentials": {}}

    used_uuids = set(old_uuids) | {v["vless_uuid"] for v in vault["credentials"].values()}
    used_pws = set(old_passwords) | {v["hy2_password"] for v in vault["credentials"].values()}

    for dev in inv["devices"]:
        dev_id = dev["device_id"]
        if dev_id not in vault["credentials"]:
            while True:
                u = str(uuid.UUID(bytes=os.urandom(16), version=4))
                if u not in used_uuids:
                    used_uuids.add(u)
                    break
            while True:
                pw = secrets.token_urlsafe(24)
                if pw not in used_pws:
                    used_pws.add(pw)
                    break
            vault["credentials"][dev_id] = {
                "v3_name": f"{dev_id}-v3",
                "vless_uuid": u,
                "hy2_password": pw,
                "status": dev.get("migration_status", "PREPARED"),
            }

    vault_path.parent.mkdir(parents=True, exist_ok=True)
    vault_path.write_text(json.dumps(vault, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return vault


def build_profile(device: dict, policy: dict, server: dict, creds: dict) -> dict:
    common = copy.deepcopy(policy["common"])
    platform = device["platform"]
    if platform not in policy["platform_tun"]:
        raise ValueError(f"Unsupported platform {platform} for {device['device_id']}")

    dns = copy.deepcopy(common["dns"])
    for dom in device.get("extra_direct_domains", []):
        pat = f"*.{dom}"
        if pat not in dns["fake-ip-filter"]:
            dns["fake-ip-filter"].append(pat)
    if device.get("extra_nameserver_policy"):
        dns["nameserver-policy"] = copy.deepcopy(device["extra_nameserver_policy"])

    proxies = [
        {
            "name": "SE-PRIMARY",
            "type": "vless",
            "server": server["domain"],
            "port": server["reality_port"],
            "uuid": creds["vless_uuid"],
            "network": "tcp",
            "tls": True,
            "udp": True,
            "packet-encoding": "xudp",
            "flow": "xtls-rprx-vision",
            "servername": server["reality_sni"],
            "client-fingerprint": server["reality_fingerprint"],
            "reality-opts": {
                "public-key": creds["reality_public_key"],
                "short-id": creds["reality_short_id"],
            },
        },
        {
            "name": "SE-HY2",
            "type": "hysteria2",
            "server": server["domain"],
            "port": server["hy2_port"],
            "password": creds["hy2_password"],
            "up": "50 Mbps",
            "down": "100 Mbps",
            "sni": server["hy2_sni"],
            "skip-cert-verify": False,
            "alpn": ["h3"],
        },
    ]

    auto_cfg = copy.deepcopy(policy["auto_group"])
    proxy_groups = [
        {
            "name": "PROXY",
            "type": "select",
            "proxies": [auto_cfg["name"], "SE-PRIMARY", "SE-HY2"],
        },
        {
            "name": auto_cfg["name"],
            "type": auto_cfg["type"],
            "proxies": auto_cfg["order"],
            "url": auto_cfg["url"],
            "interval": auto_cfg["interval"],
            "timeout": auto_cfg["timeout"],
            "lazy": auto_cfg["lazy"],
            "max-failed-times": auto_cfg["max-failed-times"],
        },
    ]

    rules = []
    for proc in device.get("extra_direct_processes", []):
        rules.append(f"PROCESS-NAME,{proc},DIRECT")
    rules.extend(creds.get("extra_cidrs", []))
    for dom in device.get("extra_direct_domains", []):
        rules.append(f"DOMAIN-SUFFIX,{dom},DIRECT")
    rules.extend(policy["base_rules"])

    seen = set()
    dedup_rules = []
    for r in rules:
        if r not in seen:
            seen.add(r)
            dedup_rules.append(r)

    return {
        "mixed-port": common["mixed-port"],
        "allow-lan": common["allow-lan"],
        "mode": common["mode"],
        "log-level": common["log-level"],
        "ipv6": common["ipv6"],
        "unified-delay": common["unified-delay"],
        "tcp-concurrent": common["tcp-concurrent"],
        "sniffer": common["sniffer"],
        "dns": dns,
        "tun": copy.deepcopy(policy["platform_tun"][platform]),
        "proxies": proxies,
        "proxy-groups": proxy_groups,
        "rules": dedup_rules,
    }


def main():
    ap = argparse.ArgumentParser(description="Generate Sweden VPN v2/v3 profiles")
    ap.add_argument("--release-version", choices=["v2", "v3"], default="v3")
    ap.add_argument("--inventory", default="tools/sweden_vpn/inventory/devices.json")
    ap.add_argument("--policy", default="tools/sweden_vpn/templates/policy_v2.yaml")
    ap.add_argument("--secrets-dir", default=r"C:\Users\Alexey\.ssh\new-vps-se")
    ap.add_argument("--private-out", default=None)
    ap.add_argument("--manifest-out", default=None)
    ap.add_argument("--auto-order", choices=["reality-first", "hy2-first"], default=None)
    args = ap.parse_args()

    ver = args.release_version
    private_out = pathlib.Path(args.private_out or f".agent-work/private-releases/sweden-{ver}")
    manifest_out = pathlib.Path(args.manifest_out or f"releases/sweden-{ver}/manifest.json")

    inv = json.loads(pathlib.Path(args.inventory).read_text(encoding="utf-8"))
    policy = yaml.safe_load(pathlib.Path(args.policy).read_text(encoding="utf-8"))
    if args.auto_order == "reality-first":
        policy["auto_group"]["order"] = ["SE-PRIMARY", "SE-HY2"]
    elif args.auto_order == "hy2-first":
        policy["auto_group"]["order"] = ["SE-HY2", "SE-PRIMARY"]

    secrets_dir = pathlib.Path(args.secrets_dir)
    if not secrets_dir.exists():
        print(f"ERROR: secrets directory not found: {secrets_dir}", file=sys.stderr)
        sys.exit(2)

    old_uuids, old_pws, ref_reality, ref_cidrs_by_dev = collect_old_secrets(inv, secrets_dir)
    vault = None
    if ver == "v3":
        vault = load_or_create_v3_vault(private_out / "vault_v3.json", inv, old_uuids, old_pws)

    private_out.mkdir(parents=True, exist_ok=True)
    manifest_out.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "release_version": ver,
        "schema_version": inv["schema_version"],
        "policy_version": "3.0.0-rc1" if ver == "v3" else policy["policy_version"],
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "auto_order": policy["auto_group"]["order"],
        "devices": [],
    }

    staging_vless = []
    staging_hy2 = []

    for dev in inv["devices"]:
        dev_id = dev["device_id"]
        if ver == "v2":
            if not dev.get("v1_file"):
                continue
            creds = extract_device_credentials(secrets_dir / dev["v1_file"])
        else:
            vc = vault["credentials"][dev_id]
            creds = {
                "vless_uuid": vc["vless_uuid"],
                "hy2_password": vc["hy2_password"],
                "reality_public_key": ref_reality[0],
                "reality_short_id": ref_reality[1],
                "extra_cidrs": ref_cidrs_by_dev.get(dev_id, []),
            }
            staging_vless.append({"name": vc["v3_name"], "uuid": vc["vless_uuid"], "flow": "xtls-rprx-vision"})
            staging_hy2.append({"name": vc["v3_name"], "password": vc["hy2_password"]})

        profile = build_profile(dev, policy, inv["server"], creds)
        dev_dir = private_out / dev_id
        dev_dir.mkdir(parents=True, exist_ok=True)
        out_yaml = dev_dir / f"{dev_id}-{ver}.yaml"
        yaml_text = yaml.safe_dump(profile, sort_keys=False, allow_unicode=True)
        out_yaml.write_text(yaml_text, encoding="utf-8")
        sha = hashlib.sha256(out_yaml.read_bytes()).hexdigest()

        (dev_dir / "SHA256SUMS.txt").write_text(f"{sha}  {out_yaml.name}\n", encoding="utf-8")
        (dev_dir / "IMPORT_AND_ROLLBACK.md").write_text(
            f"# Sweden VPN {ver} — {dev_id} ({dev['platform']} / {dev['client_app']})\n\n"
            f"- **Order:** `{' -> '.join(policy['auto_group']['order'])}`\n"
            f"- **SHA-256:** `{sha}`\n\n"
            f"## Импорт\n"
            f"1. Импортируйте `{out_yaml.name}` в `{dev['client_app']}` **без удаления** старого профиля v1.\n"
            f"2. Убедитесь, что в группе `PROXY` выбран `AUTO`.\n"
            f"3. Включите VPN/TUN и проверьте выходной IP `45.140.13.178`.\n\n"
            f"## Откат\n"
            f"Переключите активный профиль обратно на ваш прежний v1 (`{dev.get('v1_file') or 'N/A'}`).\n",
            encoding="utf-8",
        )

        manifest["devices"].append({
            "device_id": dev_id,
            "platform": dev["platform"],
            "client_app": dev["client_app"],
            "core": dev["core"],
            "profile_format": dev["profile_format"],
            "pilot": dev.get("pilot", False),
            "v1_sha256": dev.get("v1_sha256"),
            "profile_sha256": sha,
            "old_credential_dependencies": dev.get("old_credential_dependencies", []),
            "migration_status": dev.get("migration_status", "PREPARED"),
        })

    if ver == "v3":
        (private_out / "staging_singbox_users_v3.json").write_text(
            json.dumps({"vless_users_add": staging_vless, "hy2_users_add": staging_hy2}, indent=2) + "\n",
            encoding="utf-8",
        )

    manifest_out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated {len(manifest['devices'])} {ver} profiles; manifest written to {manifest_out}")


if __name__ == "__main__":
    main()
