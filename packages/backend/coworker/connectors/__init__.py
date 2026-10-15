"""Connectors: where the coworker reads from and acts through.

``workspace_for(user_id)`` returns a :class:`~coworker.connectors.base.Workspace`
that routes every read and write to the right backend: the seeded demo
workspace, or live Google and Slack accounts the user connected.
"""
from coworker.connectors.base import ConnectorError, Workspace, workspace_for

__all__ = ["ConnectorError", "Workspace", "workspace_for"]
