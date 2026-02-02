from datetime import datetime, timezone
from typing import Iterable

from db.connection import voice_sessions
from utils.time_utils import to_kst
from utils.logging_utils import log_db


async def add_voice_session(
    user_id: str,
    username: str,
    start_time: datetime,
    end_time: datetime,
    duration_seconds: int,
    log_id: str | None = None,
):
    end_kst = to_kst(end_time)
    doc = {
        "user_id": user_id,
        "username": username,
        "start_time": start_time.astimezone(timezone.utc).isoformat(),
        "end_time": end_time.astimezone(timezone.utc).isoformat(),
        "duration_seconds": int(duration_seconds),
        "kst_date": end_kst.strftime("%Y-%m-%d"),
        "kst_year": end_kst.year,
        "kst_month": end_kst.month,
        "kst_week_of_month": week_of_month(end_kst),
    }
    try:
        await voice_sessions.insert_one(doc)
        log_db("DB Writing", f"voice_sessions insert: {doc}", log_id=log_id)
    except Exception as e:
        log_db("Error", f"voice_sessions insert failed: {e}", log_id=log_id)


def week_of_month(dt_kst) -> int:
    first_day = dt_kst.replace(day=1)
    first_weekday = first_day.weekday()  # Monday=0
    return ((dt_kst.day + first_weekday - 1) // 7) + 1


def _range_query(start_kst_date: str, end_kst_date: str) -> dict:
    return {"kst_date": {"$gte": start_kst_date, "$lte": end_kst_date}}


async def aggregate_range(start_kst_date: str, end_kst_date: str, limit: int = 10, log_id: str | None = None):
    pipeline = [
        {"$match": _range_query(start_kst_date, end_kst_date)},
        {"$group": {"_id": "$user_id", "username": {"$last": "$username"}, "total_seconds": {"$sum": "$duration_seconds"}}},
        {"$sort": {"total_seconds": -1}},
        {"$limit": limit},
    ]
    try:
        cursor = voice_sessions.aggregate(pipeline)
        results = [doc async for doc in cursor]
        log_db("DB Reading", f"aggregate_range {start_kst_date}~{end_kst_date}: {len(results)} rows", log_id=log_id)
        return results
    except Exception as e:
        log_db("Error", f"aggregate_range failed: {e}", log_id=log_id)
        return []


async def aggregate_month_week(year: int, month: int, week: int, limit: int = 10, log_id: str | None = None):
    pipeline = [
        {"$match": {"kst_year": year, "kst_month": month, "kst_week_of_month": week}},
        {"$group": {"_id": "$user_id", "username": {"$last": "$username"}, "total_seconds": {"$sum": "$duration_seconds"}}},
        {"$sort": {"total_seconds": -1}},
        {"$limit": limit},
    ]
    try:
        cursor = voice_sessions.aggregate(pipeline)
        results = [doc async for doc in cursor]
        log_db("DB Reading", f"aggregate_month_week {year}-{month} W{week}: {len(results)} rows", log_id=log_id)
        return results
    except Exception as e:
        log_db("Error", f"aggregate_month_week failed: {e}", log_id=log_id)
        return []


async def aggregate_month(year: int, month: int, limit: int = 10, log_id: str | None = None):
    pipeline = [
        {"$match": {"kst_year": year, "kst_month": month}},
        {"$group": {"_id": "$user_id", "username": {"$last": "$username"}, "total_seconds": {"$sum": "$duration_seconds"}}},
        {"$sort": {"total_seconds": -1}},
        {"$limit": limit},
    ]
    try:
        cursor = voice_sessions.aggregate(pipeline)
        results = [doc async for doc in cursor]
        log_db("DB Reading", f"aggregate_month {year}-{month}: {len(results)} rows", log_id=log_id)
        return results
    except Exception as e:
        log_db("Error", f"aggregate_month failed: {e}", log_id=log_id)
        return []


async def cleanup_old_months(current_kst_date: datetime, keep_months: int = 4, log_id: str | None = None):
    # keep current month + previous (keep_months-1) months
    year = current_kst_date.year
    month = current_kst_date.month
    cutoff_month = month - (keep_months - 1)
    cutoff_year = year
    while cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1
    cutoff_str = f"{cutoff_year:04d}-{cutoff_month:02d}-01"
    try:
        result = await voice_sessions.delete_many({"kst_date": {"$lt": cutoff_str}})
        log_db("DB", f"cleanup_old_months < {cutoff_str}: {result.deleted_count} deleted", log_id=log_id)
    except Exception as e:
        log_db("Error", f"cleanup_old_months failed: {e}", log_id=log_id)
