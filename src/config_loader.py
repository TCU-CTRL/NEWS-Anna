"""YAML設定ファイルの読み込み"""

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class SourceConfig:
    """RSSソース設定"""

    name: str
    url: str
    category: str
    enabled: bool
    weight: float


@dataclass
class KeywordConfig:
    """キーワード優先度設定"""

    high_priority: list[str]
    medium_priority: list[str]
    low_priority: list[str]


def load_sources(path: str = "config/sources.yml") -> list[SourceConfig]:
    """YAMLファイルからRSSソース設定を読み込む"""
    with open(Path(path), encoding="utf-8") as f:
        data = yaml.safe_load(f)

    sources = []
    for item in data.get("sources", []):
        sources.append(
            SourceConfig(
                name=item["name"],
                url=item["url"],
                category=item["category"],
                enabled=item.get("enabled", True),
                weight=item.get("weight", 1.0),
            )
        )
    return sources


def load_keywords(path: str = "config/keywords.yml") -> KeywordConfig:
    """YAMLファイルからキーワード設定を読み込む"""
    with open(Path(path), encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return KeywordConfig(
        high_priority=data.get("high_priority", []),
        medium_priority=data.get("medium_priority", []),
        low_priority=data.get("low_priority", []),
    )
