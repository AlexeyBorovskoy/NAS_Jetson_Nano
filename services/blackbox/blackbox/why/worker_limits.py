"""Apply a bounded address-space limit inside the supervised Linux worker."""
import sys

ADDRESS_SPACE_LIMIT = 256 << 20


def apply_memory_limit(resource_module=None, platform=None):
    platform = sys.platform if platform is None else platform
    if platform != "linux":
        return True
    if resource_module is None:
        try:
            import resource as resource_module
        except ImportError:
            return False
    try:
        limit_id = resource_module.RLIMIT_AS
        soft, hard = resource_module.getrlimit(limit_id)
        target = ADDRESS_SPACE_LIMIT if soft < 0 else min(soft, ADDRESS_SPACE_LIMIT)
        if hard >= 0:
            target = min(target, hard)
        resource_module.setrlimit(limit_id, (target, hard))
        return True
    except (AttributeError, OSError, ValueError):
        return False
