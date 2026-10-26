# Java service modules

Every subdirectory is an independently runnable Spring Boot application. Initial classes expose Actuator health and basic framework wiring. Domain APIs, data access, authorization policies and event handlers must be implemented and tested before production use.

A new service requires a named owner, API/event contract, data boundary, security model, SLO, failure policy, tests and operational runbook.
