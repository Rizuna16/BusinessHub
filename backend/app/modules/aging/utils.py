from enum import Enum
from datetime import datetime, timezone
from decimal import Decimal


class AgingBucket(str, Enum):
    CURRENT = "CURRENT"
    DAYS_1_30 = "1_30"
    DAYS_31_60 = "31_60"
    DAYS_61_90 = "61_90"
    DAYS_91_120 = "91_120"
    OVER_120 = "OVER_120"


def compute_aging_days(document_date: datetime, as_of_date: datetime) -> int:
    doc_date = document_date.date() if isinstance(document_date, datetime) else document_date
    as_date = as_of_date.date() if isinstance(as_of_date, datetime) else as_of_date
    delta = as_date - doc_date
    return delta.days


def compute_aging_bucket(age_days: int) -> AgingBucket | None:
    if age_days < 0:
        return None
    if age_days == 0:
        return AgingBucket.CURRENT
    if 1 <= age_days <= 30:
        return AgingBucket.DAYS_1_30
    if 31 <= age_days <= 60:
        return AgingBucket.DAYS_31_60
    if 61 <= age_days <= 90:
        return AgingBucket.DAYS_61_90
    if 91 <= age_days <= 120:
        return AgingBucket.DAYS_91_120
    return AgingBucket.OVER_120


def bucket_field_name(bucket: AgingBucket) -> str:
    mapping = {
        AgingBucket.CURRENT: "current",
        AgingBucket.DAYS_1_30: "bucket_1_30",
        AgingBucket.DAYS_31_60: "bucket_31_60",
        AgingBucket.DAYS_61_90: "bucket_61_90",
        AgingBucket.DAYS_91_120: "bucket_91_120",
        AgingBucket.OVER_120: "bucket_over_120",
    }
    return mapping[bucket]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
