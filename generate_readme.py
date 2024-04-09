#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import datetime
import logging
from operator import attrgetter

import mdutils
import requests

MAX_ARTIFACTS = 10

logging.basicConfig()
logger = logging.getLogger(__name__)


@dataclass
class Artifact:
    name: str
    download_url: str
    created_at: datetime


def request_artifacts() -> list[Artifact]:
    artifacts: list[Artifact] = []
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    current_url = "https://api.github.com/repos/spine-tools/Spine-Toolbox/actions/artifacts"
    while current_url is not None and len(artifacts) < MAX_ARTIFACTS:
        raw_response = requests.get(current_url, headers=headers)
        current_url = None
        header_link = raw_response.headers.get("link")
        if header_link is not None:
            links = header_link.split(",")
            links = [link.split(";") for link in links]
            for link in links:
                almost_url, direction = link
                if "next" not in direction:
                    continue
                current_url = almost_url.strip()[1:-1]
                break
        response = raw_response.json()
        response_artifacts = response["artifacts"]
        for response_artifact in response_artifacts:
            if response_artifact["expired"] or not response_artifact["name"].startswith("Spine Toolbox "):
                continue
            workflow_run = response_artifact["workflow_run"]
            if workflow_run["head_branch"] != "0.8-dev":
                continue
            name = response_artifact["name"]
            artefact_id = response_artifact["id"]
            workflow_id = workflow_run["id"]
            download_url = f"https://github.com/spine-tools/Spine-Toolbox/actions/runs/{workflow_id}/artifacts/{artefact_id}"
            created_at = datetime.fromisoformat(response_artifact["created_at"])
            artifacts.append(Artifact(name, download_url, created_at))
    artifacts = artifacts[:MAX_ARTIFACTS]
    artifacts.sort(key=attrgetter("created_at"), reverse=True)
    return artifacts


def build_link(artifact: Artifact) -> str:
    label = f"{artifact.name}.zip"
    return mdutils.tools.Link.Inline.new_link(artifact.download_url, label)


def build_link_list_items(artifacts: list[Artifact]) -> list[str]:
    items = []
    for artifact in artifacts:
        items.append(f"{build_link(artifact)} ({artifact.created_at.strftime("%Y-%m-%d")})")
    return items


link_items = build_link_list_items(request_artifacts())
readme = mdutils.MdUtils(file_name="README.md", title="Downloads")
readme.new_header(level=1, title="Spine Toolbox")
readme.write(
"""
For other installation methods,
see Toolbox [installation](https://github.com/spine-tools/Spine-Toolbox?tab=readme-ov-file#installation).
"""
)
readme.new_header(level=2, title="Unstable bundles for Windows")
readme.write(
"""
Unzip and go! Bundles are zip files that contain ``spinetoolbox.exe`` executable
and everything you need to run Spine Toolbox.
They can be unzipped anywhere on your system; no other installation step is necessary.
"""
)
readme.write(
"""
The bundle also comes with a Python interpreter to help you get started.
Note, that to keep the interpreter light-weight, it is missing components like ``pip`` and ``venv``.
A separate Python installation is recommended if you need a full-blown Python for your Tools.
"""
)
readme.new_header(level=3, title="0.8 (development version)")
readme.write(
"""
Consider taking backups of your projects and Spine databases if you are upgrading from version 0.7.
"""
)
readme.new_list(link_items)
readme.create_md_file()
