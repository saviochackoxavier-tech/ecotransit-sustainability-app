"""
JSON API endpoints for EcoTransit (spec §26).

"JSON endpoints under core/api/ require session authentication, CSRF
validation, and permission checks." — Spec §26 preamble.

No Django REST Framework: the spec's tech stack section (§2) does not
name DRF, so this package uses plain Django JSON views and a small
hand-written serialization layer (core/api/serializers.py), consistent
with the dependency-minimalism principle applied since Phase 1.
"""
