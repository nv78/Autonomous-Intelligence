"""Ourogen Coworker — an AI digital coworker that works on the user's behalf.

The package is organised in layers that mirror the product epic:

* ``store``       persistence for everything the coworker knows and does
* ``connectors``  Gmail / Calendar / Slack (live) and a seeded demo workspace
* ``memory``      people graph, timeline, decision log, and recall
* ``style``       how the user writes, learned from their sent messages
* ``security``    untrusted-content handling and exfiltration checks

Later layers (agent brain, approvals, responsibilities, meetings, twin)
build on these.
"""
