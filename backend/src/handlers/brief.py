"""Brief Lambda: validates the request, re-runs the deterministic simulation, then calls Bedrock (or falls back)."""
from __future__ import annotations

from .api import ROUTES, dispatch, h_brief, PREFIX

BRIEF_ROUTES = {("POST", PREFIX + "/brief"): h_brief}


def handler(event, context=None):
    return dispatch(event, BRIEF_ROUTES)
