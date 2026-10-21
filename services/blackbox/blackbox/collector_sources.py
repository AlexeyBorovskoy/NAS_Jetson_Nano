"""Источники сборщика по умолчанию (OBS-1, задача 7).

`DefaultSources` связывает расписание сборщика с настоящими модулями задач
2–6 **ровно по их сигнатурам**: `sysfs.read_fast_sample(cfg, prev_cpu, ts)`,
`procs.read_procs(proc_root, resolver)` + `procs.snapshot(prev, cur, dt_s, hz,
ts)`, `DockerClient.events(since_ts)` (аргумент обязателен),
`probes.probe_gateway(run)`, `probes.probe_dns(..., run=...)`,
`probes.probe_tunnel(proc_root, vps_hosts)`, `probes.probe_tcp(host, port,
timeout)`.

Единственный экземпляр `MountProbe` на HDD: `poll(now)` — единственный
способ обратиться к `/mnt/hdd2tb`, в своём процессе этот путь не читается.
Пустой `cfg.vps_hosts` означает «адреса VPS неизвестны»: сборщик не читает
`.env` и не подставляет адреса сам, проба туннеля просто не вызывается.

Python 3.6 (хост Jetson): только стандартная библиотека.
"""
import os
import subprocess

from blackbox.collector_events import TAIL_LINES_MAX, _safe
from blackbox.sources import container_logs, docker_api, journal, probes, procs, sysfs

#: TCP-проба прокси Telegram (спецификация §4.1).
TG_PROXY_HOST = "172.17.0.1"
TG_PROXY_PORT = 1080
PROBE_TCP_TIMEOUT = 3


def _clock_hz():
    """Тиков на секунду для CPU-процентов (Linux — SC_CLK_TCK, иначе 100)."""
    try:
        return int(os.sysconf("SC_CLK_TCK"))
    except (AttributeError, ValueError, OSError):
        return 100


_HZ = _clock_hz()


class DefaultSources(object):
    """Настоящие модули задач 2–6, собранные в один объект источников."""

    def __init__(self, cfg, run=None, docker_client=None, mount_probe=None,
                 log_state=None):
        self.cfg = cfg
        self._run = run if run is not None else subprocess.run
        self._docker = (docker_client if docker_client is not None
                        else docker_api.DockerClient(cfg.docker_sock))
        self.mount_probe = (mount_probe if mount_probe is not None
                            else probes.MountProbe(cfg.hdd_mount))
        self.log_state = log_state if log_state is not None else {}
        self._tailer = container_logs.LogTailer(
            self.log_state, initial_tail_bytes=16 << 10)

    # задача 2: секундный замер
    def read_fast_sample(self, cfg, prev_cpu, ts):
        return sysfs.read_fast_sample(cfg, prev_cpu, ts)

    # задача 6: процессы; резолвер owner — из карты контейнеров Docker
    def read_procs(self, proc_root, container_of=None):
        if container_of is None:
            container_of = procs.container_of(proc_root, self._id_map())
        return procs.read_procs(proc_root, container_of)

    def _id_map(self):
        containers = _safe(self.containers, []) or []
        return dict((item.get("id"), item.get("name")) for item in containers
                    if item.get("id"))

    def snapshot(self, prev_raw, cur_raw, dt_s, hz, ts, top_n=10):
        return procs.snapshot(prev_raw, cur_raw, dt_s, hz, ts, top_n)

    def is_anomaly(self, sample, prev_sample, d_count, cfg):
        return procs.is_anomaly(sample, prev_sample, d_count, cfg)

    # задача 4: Docker — сокет, события, журналы
    def containers(self):
        return self._docker.containers()

    def events(self, since_ts):
        return self._docker.events(since_ts)

    def read_new(self, name, path, max_bytes):
        return self._tailer.read_new(name, path, max_bytes)

    def tail_lines(self, path, n=TAIL_LINES_MAX):
        return container_logs.tail_lines(path, n)

    event_from_docker = staticmethod(docker_api.event_from_docker)
    split_health = staticmethod(container_logs.split_health)

    # задача 5: журнал и пробы
    def journal_since(self, cursor, run=None):
        return journal.journal_since(cursor, self._run)

    def probe_gateway(self):
        return probes.probe_gateway(self._run)

    def probe_dns(self):
        return probes.probe_dns(run=self._run)

    def probe_tunnel(self):
        return probes.probe_tunnel(self.cfg.proc_root, self.cfg.vps_hosts)

    def probe_tcp(self, host, port, timeout=PROBE_TCP_TIMEOUT):
        return probes.probe_tcp(host, port, timeout)

    def probes_event(self, results, prev):
        return probes.probes_event(results, prev)
