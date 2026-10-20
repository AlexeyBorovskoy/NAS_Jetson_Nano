#!/usr/bin/env python3
"""Show or toggle Immich nightlyTasks.missingThumbnails with read-verify-write."""

import argparse
import contextlib
import copy
import datetime
import json
import logging
import os
import urllib.error
import urllib.request

API_URL, CONFIG_PATH = "http://localhost:2283", "/api/system-config"
API_KEY_ENV = "IMMICH_API_KEY"
TIMEOUT_SECONDS = 30
TARGET = ("nightlyTasks", "missingThumbnails")
LOG = logging.getLogger("immich-nightly")

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class ConfigError(Exception):
    """Shape, state or verification problem; messages never carry values."""

def flag_value(config, path=TARGET):
    """Return the boolean at path, rejecting anything that is not a bool."""
    node = config
    for key in path:
        if not isinstance(node, dict) or key not in node:
            raise ConfigError("missing field: %s" % ".".join(path))
        node = node[key]
    if not isinstance(node, bool):
        raise ConfigError("not a boolean: %s" % ".".join(path))
    return node

def change_flag(config, enabled):
    if not isinstance(config, dict):
        raise ConfigError("config must be an object")
    if not isinstance(enabled, bool):
        raise ConfigError("enabled must be a boolean")
    flag_value(config)
    changed = copy.deepcopy(config)
    changed[TARGET[0]][TARGET[1]] = enabled
    return changed

@contextlib.contextmanager
def transport():
    """Yield an opener with a 30 s timeout; log status or error type only."""
    def opener(request):
        try:
            client = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            return client.open(request, timeout=TIMEOUT_SECONDS)
        except urllib.error.HTTPError as exc:
            LOG.error("HTTP status %s", exc.code)
            raise
        except Exception as exc:
            LOG.error("transport error: %s", type(exc).__name__)
            raise
    yield opener

def _request(opener, method, payload=None):
    if not os.environ.get(API_KEY_ENV):
        raise ConfigError("IMMICH_API_KEY is not set")
    headers = {"x-api-key": os.environ[API_KEY_ENV], "Accept": "application/json"}
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        API_URL + CONFIG_PATH, data=data, headers=headers, method=method)
    response = opener(request)
    try:
        return response.read()
    finally:
        response.close()

def fetch_config(opener):
    try:
        config = json.loads(_request(opener, "GET").decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ConfigError("system-config response is not valid JSON")
    if not isinstance(config, dict):
        raise ConfigError("system-config response is not an object")
    return config

def put_config(opener, config):
    _request(opener, "PUT", config)

def write_backup(prior_enabled):
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    folder = os.path.join(root, ".agent-work", "archives", "immich-nightly")
    os.makedirs(folder, mode=0o700, exist_ok=True)
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(folder, "nightly-thumbnails-%s-%s.json" % (stamp, os.getpid()))
    record = {"createdUtc": stamp, "nightlyTasks": {"missingThumbnails": prior_enabled}}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(record, indent=2) + "\n")
    return path

def read_backup_flag(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError):
        raise ConfigError("backup cannot be read")
    return flag_value(record)

def _apply(opener, first, desired, prior):
    LOG.info("rollback record: %s", write_backup(prior))
    if fetch_config(opener) != first:
        raise ConfigError("config changed between reads; refusing to write")
    put_config(opener, desired)
    if fetch_config(opener) != desired:
        raise ConfigError("post-write verification failed; config differs from desired")

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--disable", action="store_true")
    group.add_argument("--restore", metavar="BACKUP")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        with transport() as opener:
            config = fetch_config(opener)
            if not args.disable and not args.restore:
                print("nightlyTasks.missingThumbnails=%s\nlibrary.scan.enabled=%s"
                      % (str(flag_value(config)).lower(),
                         str(flag_value(config, ("library", "scan", "enabled"))).lower()))
                return 0
            if args.disable:
                if flag_value(config) is False:
                    print("nightlyTasks.missingThumbnails already false; no write")
                    return 0
                desired = change_flag(config, False)
            else:
                desired = change_flag(config, read_backup_flag(args.restore))
                if desired == config:
                    print("nightlyTasks.missingThumbnails matches backup; no write")
                    return 0
            _apply(opener, config, desired, flag_value(config))
            print("nightlyTasks.missingThumbnails=%s; verification ok"
                  % str(flag_value(desired)).lower())
            return 0
    except ConfigError as exc:
        LOG.error("%s", exc)
        return 1
    except Exception as exc:
        LOG.error("failed: %s", type(exc).__name__)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
