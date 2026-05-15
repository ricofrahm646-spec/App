"""
JARVIS Service Manager — Central orchestrator for all system services.

Handles initialization, health aggregation, graceful startup/shutdown,
and provides a service registry for dependency lookup.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

import structlog

logger = structlog.get_logger("jarvis.service_manager")


class ServiceStatus(str, Enum):
    REGISTERED = "registered"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ServiceInfo:
    """Metadata and runtime state for a registered service."""

    name: str
    status: ServiceStatus = ServiceStatus.REGISTERED
    instance: Any = None
    started_at: Optional[float] = None
    last_health_check: Optional[float] = None
    health_message: str = ""
    startup_order: int = 0
    dependencies: List[str] = field(default_factory=list)
    _start_fn: Optional[Callable[[], Coroutine]] = field(default=None, repr=False)
    _stop_fn: Optional[Callable[[], Coroutine]] = field(default=None, repr=False)
    _health_fn: Optional[Callable[[], Coroutine]] = field(default=None, repr=False)

    @property
    def uptime_seconds(self) -> float:
        if self.started_at is None:
            return 0.0
        return round(time.monotonic() - self.started_at, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "uptime_seconds": self.uptime_seconds,
            "last_health_check": self.last_health_check,
            "health_message": self.health_message,
        }


class ServiceManager:
    """Central registry and lifecycle manager for all JARVIS services.

    Usage::

        manager = ServiceManager()

        manager.register(
            name="database",
            instance=db_manager,
            start_fn=db_manager.create_all,
            stop_fn=db_manager.close,
            health_fn=db_manager.health_check,
            startup_order=0,
        )

        manager.register(
            name="redis",
            instance=redis_pool,
            start_fn=redis_pool.connect,
            stop_fn=redis_pool.close,
            health_fn=redis_pool.ping,
            startup_order=1,
        )

        await manager.start_all()
        # ...
        await manager.stop_all()
    """

    def __init__(self) -> None:
        self._services: Dict[str, ServiceInfo] = {}
        self._started = False
        self._start_time: Optional[float] = None

    # ── Registration ─────────────────────────────────────────────────

    def register(
        self,
        name: str,
        instance: Any = None,
        start_fn: Optional[Callable[[], Coroutine]] = None,
        stop_fn: Optional[Callable[[], Coroutine]] = None,
        health_fn: Optional[Callable[[], Coroutine]] = None,
        startup_order: int = 100,
        dependencies: Optional[List[str]] = None,
    ) -> None:
        """Register a service with the manager.

        Args:
            name: Unique service identifier.
            instance: The service object (for dependency lookup).
            start_fn: Async callable invoked during startup.
            stop_fn: Async callable invoked during shutdown.
            health_fn: Async callable returning ``True`` if healthy.
            startup_order: Lower numbers start first.
            dependencies: Names of services that must start before this one.
        """
        if name in self._services:
            logger.warning("service_already_registered", service=name)
            return

        self._services[name] = ServiceInfo(
            name=name,
            instance=instance,
            startup_order=startup_order,
            dependencies=dependencies or [],
            _start_fn=start_fn,
            _stop_fn=stop_fn,
            _health_fn=health_fn,
        )
        logger.info("service_registered", service=name, order=startup_order)

    def unregister(self, name: str) -> None:
        """Remove a service from the registry."""
        if name in self._services:
            del self._services[name]
            logger.info("service_unregistered", service=name)

    # ── Service lookup ───────────────────────────────────────────────

    def get(self, name: str) -> Any:
        """Retrieve a service instance by name.

        Raises:
            KeyError: If the service is not registered.
        """
        info = self._services.get(name)
        if info is None:
            raise KeyError(f"Service '{name}' is not registered")
        return info.instance

    def get_info(self, name: str) -> Optional[ServiceInfo]:
        """Retrieve service metadata by name."""
        return self._services.get(name)

    @property
    def services(self) -> Dict[str, ServiceInfo]:
        return dict(self._services)

    @property
    def service_names(self) -> List[str]:
        return list(self._services.keys())

    # ── Startup ──────────────────────────────────────────────────────

    async def start_all(self) -> Dict[str, bool]:
        """Start all registered services in dependency/startup-order.

        Returns:
            Dict mapping service names to success booleans.
        """
        results: Dict[str, bool] = {}
        ordered = self._resolve_startup_order()

        logger.info(
            "starting_all_services",
            count=len(ordered),
            order=[s.name for s in ordered],
        )
        self._start_time = time.monotonic()

        for svc in ordered:
            success = await self._start_service(svc)
            results[svc.name] = success

        self._started = True
        healthy = sum(1 for v in results.values() if v)
        logger.info(
            "all_services_started",
            healthy=healthy,
            total=len(results),
        )
        return results

    async def _start_service(self, svc: ServiceInfo) -> bool:
        """Start a single service with error handling."""
        svc.status = ServiceStatus.STARTING
        logger.info("service_starting", service=svc.name)

        if svc._start_fn is not None:
            try:
                await svc._start_fn()
                svc.status = ServiceStatus.HEALTHY
                svc.started_at = time.monotonic()
                svc.health_message = "Started successfully"
                logger.info("service_started", service=svc.name)
                return True
            except Exception as exc:
                svc.status = ServiceStatus.FAILED
                svc.health_message = f"Start failed: {exc}"
                logger.error(
                    "service_start_failed",
                    service=svc.name,
                    error=str(exc),
                )
                return False
        else:
            svc.status = ServiceStatus.HEALTHY
            svc.started_at = time.monotonic()
            svc.health_message = "No start function (passive service)"
            return True

    # ── Shutdown ─────────────────────────────────────────────────────

    async def stop_all(self) -> Dict[str, bool]:
        """Gracefully stop all services in reverse startup order.

        Returns:
            Dict mapping service names to success booleans.
        """
        results: Dict[str, bool] = {}
        ordered = list(reversed(self._resolve_startup_order()))

        logger.info(
            "stopping_all_services",
            count=len(ordered),
            order=[s.name for s in ordered],
        )

        for svc in ordered:
            success = await self._stop_service(svc)
            results[svc.name] = success

        self._started = False
        logger.info("all_services_stopped")
        return results

    async def _stop_service(self, svc: ServiceInfo) -> bool:
        """Stop a single service with error handling."""
        if svc._stop_fn is not None:
            try:
                await svc._stop_fn()
                svc.status = ServiceStatus.STOPPED
                svc.health_message = "Stopped gracefully"
                logger.info("service_stopped", service=svc.name)
                return True
            except Exception as exc:
                svc.status = ServiceStatus.FAILED
                svc.health_message = f"Stop failed: {exc}"
                logger.error(
                    "service_stop_failed",
                    service=svc.name,
                    error=str(exc),
                )
                return False
        else:
            svc.status = ServiceStatus.STOPPED
            return True

    # ── Health checks ────────────────────────────────────────────────

    async def check_health(self) -> Dict[str, Any]:
        """Run health checks for all services and return an aggregate report.

        Returns:
            Dict with per-service status and an overall summary.
        """
        service_health: Dict[str, Any] = {}
        healthy_count = 0
        total = len(self._services)

        tasks = {
            name: self._check_service_health(info)
            for name, info in self._services.items()
        }

        results = await asyncio.gather(
            *tasks.values(), return_exceptions=True
        )

        for name, result in zip(tasks.keys(), results):
            info = self._services[name]

            if isinstance(result, Exception):
                info.status = ServiceStatus.UNHEALTHY
                info.health_message = str(result)
                is_healthy = False
            else:
                is_healthy = bool(result)
                if is_healthy:
                    info.status = ServiceStatus.HEALTHY
                    info.health_message = "OK"
                    healthy_count += 1
                else:
                    info.status = ServiceStatus.UNHEALTHY
                    info.health_message = "Health check returned False"

            info.last_health_check = time.time()
            service_health[name] = info.to_dict()

        if healthy_count == total:
            overall = "healthy"
        elif healthy_count > 0:
            overall = "degraded"
        else:
            overall = "unhealthy"

        uptime = 0.0
        if self._start_time:
            uptime = round(time.monotonic() - self._start_time, 2)

        return {
            "status": overall,
            "uptime_seconds": uptime,
            "services": service_health,
            "summary": {
                "total": total,
                "healthy": healthy_count,
                "unhealthy": total - healthy_count,
            },
        }

    async def _check_service_health(self, info: ServiceInfo) -> bool:
        """Run health check for a single service."""
        if info._health_fn is None:
            return info.status in (
                ServiceStatus.HEALTHY,
                ServiceStatus.DEGRADED,
            )
        return await info._health_fn()

    # ── Ordering ─────────────────────────────────────────────────────

    def _resolve_startup_order(self) -> List[ServiceInfo]:
        """Topological sort by dependencies, then by startup_order."""
        visited: set[str] = set()
        result: List[ServiceInfo] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            info = self._services.get(name)
            if info is None:
                return
            for dep in info.dependencies:
                visit(dep)
            result.append(info)

        by_order = sorted(
            self._services.values(), key=lambda s: s.startup_order
        )
        for svc in by_order:
            visit(svc.name)

        return result

    # ── Utilities ────────────────────────────────────────────────────

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def is_healthy(self) -> bool:
        return all(
            info.status in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED)
            for info in self._services.values()
        )

    def summary(self) -> Dict[str, str]:
        """Quick status summary of all services."""
        return {
            name: info.status.value for name, info in self._services.items()
        }

    def __repr__(self) -> str:
        svcs = ", ".join(
            f"{name}={info.status.value}"
            for name, info in self._services.items()
        )
        return f"ServiceManager({svcs})"


# ── Module-level singleton ───────────────────────────────────────────────

_manager: Optional[ServiceManager] = None


def get_service_manager() -> ServiceManager:
    """Return the global ServiceManager singleton."""
    global _manager
    if _manager is None:
        _manager = ServiceManager()
    return _manager
