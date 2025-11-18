"""
Service Container - Dependency Injection System
==============================================
Core infrastructure for managing services and their dependencies.
Provides automatic dependency resolution and service lifecycle management.
"""

import logging
import traceback
from typing import Dict, Any, Callable, List, Optional, Type
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class ServiceTier(Enum):
    """Service criticality levels for tiered startup"""
    CRITICAL = "critical"      # App won't start without these
    IMPORTANT = "important"    # Reduced functionality if missing
    OPTIONAL = "optional"      # Nice to have, fail silently

@dataclass
class ServiceDefinition:
    """Definition of a service for the container"""
    name: str
    factory: Callable
    dependencies: List[str]
    tier: ServiceTier
    singleton: bool = True
    lazy: bool = True

class ServiceContainer:
    """
    Dependency injection container that manages service lifecycle
    and automatic dependency resolution.
    """

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._definitions: Dict[str, ServiceDefinition] = {}
        self._initializing: set = set() # Prevent circular dependencies
        self._failed_services: Dict[str, str] = {} # service_name -> error_message

    def register(self, 
                name: str,
                factory: Callable,
                dependencies: List[str] = None,
                tier: ServiceTier = ServiceTier.IMPORTANT,
                singleton: bool = True,
                lazy: bool = True):
        """Register a service with the container"""

        if dependencies is None:
            dependencies = []

        definition = ServiceDefinition(
            name=name,
            factory=factory,
            dependencies=dependencies,
            tier=tier,
            singleton=singleton,
            lazy=lazy
        )

        self._definitions[name] = definition
        logger.debug(f"Registered service: {name} (tier: {tier.value})")
        return self # Allow method chaining

    def get(self, service_name: str) -> Any:
        """Get a service instance, initializing if necessary"""

        # Return cached instance if singleton
        if service_name in self._services:
            return self._services[service_name]

        # Check if service failed previously
        if service_name in self._failed_services:
            error_msg = self._failed_services[service_name]
            raise ServiceUnavailableError(f"Service {service_name} previously failed: {error_msg}")

        # Check if service is registered
        if service_name not in self._definitions:
            raise ServiceNotFoundError(f"Service {service_name} not registered")

        return self._initialize_service(service_name)

    def _initialize_service(self, service_name: str) -> Any:
        """Initialize a service and its dependencies"""

        # Prevent circular dependencies
        if service_name in self._initializing:
            raise CircularDependencyError(f"Circular dependency detected for service: {service_name}")

        try:
            self._initializing.add(service_name)
            definition = self._definitions[service_name]

            logger.debug(f"Initializing service: {service_name}")

            # Initialize dependencies first
            dependency_instances = {}
            for dep_name in definition.dependencies:
                try:
                    dependency_instances[dep_name] = self.get(dep_name)
                except Exception as e:
                    # Handle dependency failure based on service tier
                    if definition.tier == ServiceTier.CRITICAL:
                        raise ServiceInitializationError(
                            f"Critical service {service_name} failed due to dependency {dep_name}: {e}"
                        )
                    else:
                        logger.warning(f"Non-critical dependency {dep_name} failed for {service_name}: {e}")

            # Create service instance
            try:
                instance = definition.factory(**dependency_instances)
            except Exception as e:
                error_msg = f"Failed to initialize service {service_name}: {e}"
                self._failed_services[service_name] = error_msg
                logger.error(error_msg)
                logger.error(traceback.format_exc())
                raise ServiceInitializationError(error_msg)

            # Cache instance if singleton
            if definition.singleton:
                self._services[service_name] = instance

            return instance

        finally:
            # Always remove from initializing set, even on exception
            self._initializing.remove(service_name)

    def initialize_tier(self, tier: ServiceTier) -> Dict[str, bool]:
        """Initialize all services of a specific tier"""

        results = {}
        services_in_tier = [
            name for name, definition in self._definitions.items()
            if definition.tier == tier
        ]

        logger.info(f"Initializing {len(services_in_tier)} {tier.value} services")

        for service_name in services_in_tier:
            try:
                self.get(service_name)
                results[service_name] = True
                logger.info(f"[OK] {service_name} initialized successfully")
            except Exception as e:
                results[service_name] = False
                if tier == ServiceTier.CRITICAL:
                    logger.error(f"[FAIL] Critical service {service_name} failed: {e}")
                    raise
                else:
                    logger.warning(f"[WARN] {tier.value} service {service_name} failed: {e}")

        return results

    def is_available(self, service_name: str) -> bool:
        """Check if a service is available without initializing it"""

        if service_name in self._services:
            return True

        if service_name in self._failed_services:
            return False

        if service_name not in self._definitions:
            return False

        # For lazy services, we can't know without trying to initialize
        # For critical services, assume available if registered
        definition = self._definitions[service_name]
        return definition.tier == ServiceTier.CRITICAL

    def get_service_info(self, service_name: str) -> Dict[str, Any]:
        """Get information about a service"""

        if service_name not in self._definitions:
            return {"status": "not_registered"}

        definition = self._definitions[service_name]
        info = {
            "name": service_name,
            "tier": definition.tier.value,
            "dependencies": definition.dependencies,
            "singleton": definition.singleton,
            "lazy": definition.lazy
        }

        if service_name in self._services:
            info["status"] = "initialized"
            info["instance"] = type(self._services[service_name]).__name__
        elif service_name in self._failed_services:
            info["status"] = "failed"
            info["error"] = self._failed_services[service_name]
        else:
            info["status"] = "registered"

        return info

    def get_all_services_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered services"""

        return {
            name: self.get_service_info(name)
            for name in self._definitions.keys()
        }

    def shutdown(self):
        """Shutdown all services gracefully"""

        logger.info("Shutting down service container")

        # Shutdown in reverse dependency order
        for service_name, service_instance in self._services.items():
            try:
                if hasattr(service_instance, 'shutdown'):
                    service_instance.shutdown()
                    logger.debug(f"Shutdown service: {service_name}")
            except Exception as e:
                logger.error(f"Error shutting down service {service_name}: {e}")

        self._services.clear()
        self._failed_services.clear()

# Exception classes for service container
class ServiceContainerError(Exception):
    """Base exception for service container errors"""
    pass

class ServiceNotFoundError(ServiceContainerError):
    """Service not registered in container"""
    pass

class ServiceInitializationError(ServiceContainerError):
    """Service failed to initialize"""
    pass

class ServiceUnavailableError(ServiceContainerError):
    """Service is unavailable due to previous failure"""
    pass

class CircularDependencyError(ServiceContainerError):
    """Circular dependency detected"""
    pass
