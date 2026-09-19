"""D3: установщик на VPS — статические гарантии (правило №13, спецификация §5).

Установщик выполняется только на VPS по «деплой», поэтому здесь проверяется
текст: ключ с единственной командой, sshd не перезапускается, sshd -t есть,
Amnezia/nginx/docker не упоминаются.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "..", "services", "watchdog", "vps", "install_vps.sh")


def src():
    return open(SCRIPT, encoding="utf-8").read()


def test_key_is_restricted_to_one_command():
    assert 'restrict,command="/usr/local/bin/nas-liveness"' in src()


def test_sshd_config_checked_and_never_restarted():
    s = src()
    assert "sshd -t" in s
    assert not re.search(r"systemctl\s+(restart|reload|stop)\s+ssh", s)


def test_does_not_touch_vpn_or_proxy_or_docker():
    s = src().lower()
    for word in ("amnezia", "nginx", "docker", "ufw", "iptables"):
        assert word not in s, word


def test_only_ed25519_keys_accepted():
    assert "ssh-ed25519" in src()


def test_password_is_not_locked_style():
    # «!» в shadow OpenSSH считает заблокированным аккаунтом и может отказать во входе по ключу.
    assert "usermod -p '*' naswatch" in src()


def test_idempotent_authorized_keys():
    assert "grep -qxF" in src()


def test_multiline_key_rejected():
    assert "*$'\\n'*" in src()


def test_home_dir_mode_is_explicit():
    s = src()
    assert "chmod 0750 /var/lib/naswatch" in s
    assert "chown naswatch:naswatch /var/lib/naswatch" in s
