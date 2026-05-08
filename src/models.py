"""記事データモデル定義"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    """RSSから取得した記事を表すデータクラス"""

    title: str
    url: str
    source: str
    category: str
    published_at: datetime | None
    summary: str
    score: float = field(default=0.0)
