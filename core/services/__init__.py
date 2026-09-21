"""
Core service-layer modules: pure business logic, independent of any view,
form, or API endpoint (those are later phases).

Modules:
    carbon      — carbon-saving calculation engine
    openroute   — OpenRouteService (ORS) routing/geocoding wrapper
    integrity   — SHA-256 journey integrity hashing

Not present yet: points/streak logic helpers. The v2.1.1 spec text
available at implementation time does not define the points-per-km/mode
values or the streak continuity/reset rules, and point/streak logic is
named as a frozen decision that must not be invented without approval.
See README.md "Phase 3" section for what's needed to unblock this.
"""
