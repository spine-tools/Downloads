#!/usr/bin/env python3

from dataclasses import dataclass
from datetime import datetime
import logging
from operator import attrgetter
from typing import Union

import mdutils
import requests

MAX_ARTIFACTS = 10

logging.basicConfig()
logger = logging.getLogger(__name__)

headers = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}


@dataclass
class Artifact:
    name: str
    download_url: str
    created_at: datetime

    def md_link(self) -> str:
        label = f"{self.name}.zip"
        return mdutils.tools.Link.Inline.new_link(self.download_url, label)


@dataclass
class ReleaseAsset:
    version: str
    name: str
    download_url: str
    created_at: datetime

    def md_link(self) -> str:
        return mdutils.tools.Link.Inline.new_link(self.download_url, self.name)


def request_artifacts() -> list[Artifact]:
    artifacts: list[Artifact] = []
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
            if response_artifact["expired"] or not response_artifact["name"].startswith("Spine-Toolbox-win"):
                continue
            workflow_run = response_artifact["workflow_run"]
            if workflow_run["head_branch"] != "master":
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


def build_link_list_items(items: list[Union[Artifact, ReleaseAsset]]) -> list[str]:
    link_items: list[str] = []
    for item in items:
        link_items.append(f"{item.md_link()} ({item.created_at.strftime("%Y-%m-%d")})")
    return link_items


snapshot_link_items = build_link_list_items(request_artifacts())


def request_release_assets() -> list[ReleaseAsset]:
    assets: list[ReleaseAsset] = []
    url = "https://api.github.com/repos/spine-tools/Spine-Toolbox/releases"
    raw_response = requests.get(url, headers=headers)
    response = raw_response.json()
    for release in response:
        created_at = datetime.fromisoformat(release["published_at"])
        if created_at < datetime(year=2024, month=5, day=1, tzinfo=created_at.tzinfo):
            # The installers before the 0.8 bundles are not recommended for users.
            continue
        version = release["tag_name"]
        assets_url = release["assets_url"]
        assets_raw_response = requests.get(assets_url, headers=headers)
        assets_response = assets_raw_response.json()
        for asset in assets_response:
            name = asset["name"]
            download_url = asset["browser_download_url"]
            assets.append(ReleaseAsset(version, name, download_url, created_at))
    return sorted(assets, key=attrgetter("created_at"), reverse=True)


release_link_items = build_link_list_items(request_release_assets())

readme = mdutils.MdUtils(file_name="README.md", title="Downloads")
readme.new_header(level=1, title="Spine Toolbox")
readme.new_header(level=2, title="Relocatable bundles for Windows")
readme.write(
"""
Unzip and go! Bundles are zip files that contain ``spinetoolbox.exe`` executable
and everything you need to run Spine Toolbox.
They can be unzipped anywhere on your system; no other installation steps are necessary.
"""
)
readme.write(
"""
The bundle also comes with a Python interpreter to help you get started.
Note, that to keep the interpreter light-weight, it is missing components like ``pip`` and ``venv``.
A separate Python installation is recommended if you need a full-blown Python for your Tools.
"""
)
readme.write(
"""
For other installation methods,
see Toolbox [installation](https://github.com/spine-tools/Spine-Toolbox?tab=readme-ov-file#installation).
"""
)
readme.new_header(level=3, title="Releases")
readme.write(
"""
Consider taking backups of your projects and Spine databases if you are upgrading from version 0.7.x.
"""
)
readme.new_header(level=4, title="Latest")
readme.new_list([release_link_items[0]])
if len(release_link_items) > 1:
    readme.new_header(level=4, title="Older releases")
    readme.new_list(release_link_items[1:])
readme.new_header(level=3, title="Development snapshots")
readme.new_list(snapshot_link_items)
readme.create_md_file()
