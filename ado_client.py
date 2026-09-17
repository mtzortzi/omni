"""Azure DevOps client factory.

Loads credentials from .env and returns authenticated SDK clients.
Never log or print the PAT.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from msrest.authentication import BasicAuthentication
from azure.devops.connection import Connection
from azure.devops.v7_1.work_item_tracking.work_item_tracking_client import (
    WorkItemTrackingClient,
)
from azure.devops.v7_1.work.work_client import WorkClient


@dataclass(frozen=True)
class AdoConfig:
    org_url: str
    pat: str
    project: str

    @classmethod
    def from_env(cls) -> "AdoConfig":
        # Load the .env that sits next to this module, regardless of the
        # current working directory, so scripts work when invoked from any path.
        load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))
        org_url = os.environ.get("ADO_ORG_URL", "").strip()
        pat = os.environ.get("ADO_PAT", "").strip()
        project = os.environ.get("ADO_PROJECT", "").strip()
        missing = [
            name
            for name, val in [
                ("ADO_ORG_URL", org_url),
                ("ADO_PAT", pat),
                ("ADO_PROJECT", project),
            ]
            if not val
        ]
        if missing:
            raise RuntimeError(
                f"Missing required env vars: {', '.join(missing)}. "
                "Copy .env.example to .env and fill it in."
            )
        return cls(org_url=org_url, pat=pat, project=project)


def get_clients(
    config: AdoConfig | None = None,
) -> tuple[WorkItemTrackingClient, WorkClient]:
    """Return (WorkItemTrackingClient, WorkClient)."""
    cfg = config or AdoConfig.from_env()
    creds = BasicAuthentication("", cfg.pat)  # empty username, PAT as password
    conn = Connection(base_url=cfg.org_url, creds=creds)
    wit_client = conn.clients.get_work_item_tracking_client()
    work_client = conn.clients.get_work_client()
    return wit_client, work_client
