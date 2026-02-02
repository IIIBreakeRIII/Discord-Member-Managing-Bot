from datetime import datetime, timezone

from db.connection import userlogs as collection
from utils.logging_utils import log_db

# Update User Voice Log In DB
async def update_user_voice_log(
    user_id: str,
    username: str = None,
    join_time: datetime = None,
    leave_time: datetime = None,
    channel: str = None,
    log_id: str | None = None,
):
    update_fields = {}

    if join_time:
        update_fields["join_time"] = join_time.astimezone(timezone.utc).isoformat()
        update_fields["last_active"] = join_time.astimezone(timezone.utc).isoformat()

    if leave_time:
        update_fields["leave_time"] = leave_time.astimezone(timezone.utc).isoformat()

    if channel:
        update_fields["channel"] = channel

    if username:
        update_fields["username"] = username

    if not update_fields:
        log_db("DB", "update_user_voice_log: update_fields empty — skip write", log_id=log_id)
        return

    log_db("DB Writing", f"update_user_voice_log: {update_fields}", log_id=log_id)

    try:
        result = await collection.update_one(
            {"user_id": user_id},
            {"$set": update_fields},
            upsert=True
        )
        log_db("DB", f"MongoDB write result: {result.raw_result}", log_id=log_id)
    except Exception as e:
        log_db("Error", f"MongoDB write failed: {e}", log_id=log_id)

# Get Last Active Time -> To User
async def get_last_active_by_user_id(user_id: str, log_id: str | None = None) -> str | None:
    doc = await collection.find_one({"user_id": user_id})
    log_db("DB", f"User doc: {doc}", log_id=log_id)
    if doc and "last_active" in doc:
        return doc["last_active"]
    return None

# Save Role in DB
async def save_granted_role(user_id: str, username: str, role_name: str, log_id: str | None = None):
    doc = {
        "user_id": user_id,
        "username": username,
        "granted_role": role_name,
        "granted_time": datetime.now(timezone.utc).isoformat(),
    }

    log_db("DB Writing", f"Saving granted role: {doc}", log_id=log_id)
    
    try:
        await collection.update_one(
            {"user_id": user_id},
            {"$set": doc},
            upsert=True
        )
    except Exception as e:
        log_db("Error", f"MongoDB save failed: {e}", log_id=log_id)

# Save User's Server Enter Time in DB
async def save_join_time(user_id: str, username: str, log_id: str | None = None):
    doc = { "user_id": user_id, "username": username , "joined_at_server": datetime.now(timezone.utc).isoformat(), }
    
    log_db("DB Writing", f"Saving join time: {doc}", log_id=log_id)

    try:
        await collection.update_one(
            {"user_id": user_id},
            {"$setOnInsert": doc},
            upsert=True
        )
    except Exception as e:
        log_db("Error", f"MongoDB save failed (join time): {e}", log_id=log_id)

# User Voice Duration Time
async def get_total_voice_duration(user_id: str, log_id: str | None = None) -> int:
    """
    MongoDB에서 해당 유저의 전체 접속 시간 누적을 초 단위로 반환
    """
    doc = await collection.find_one({"user_id": user_id})
    log_db("DB", f"Voice duration doc: {doc}", log_id=log_id)
    if doc and "durations" in doc:
        return int(doc["durations"].get("total_seconds", 0))
    return 0

async def add_voice_duration(user_id: str, username: str, duration_seconds: int, log_id: str | None = None):
    try:
        await collection.update_one(
            {"user_id": user_id},
            {
                "$set": {"username": username},
                "$inc": {"durations.total_seconds": duration_seconds}
            },
            upsert=True
        )
        log_db("DB", f"Voice duration updated: {username} +{duration_seconds}s", log_id=log_id)
    except Exception as e:
        log_db("Error", f"Voice duration update failed: {e}", log_id=log_id)

# Server Synchronization to DB
async def upsert_member_info(data: dict, log_id: str | None = None):
    """
    유저 정보를 user_id 기준으로 최신화하거나 새로 삽입
    """
    try:
        await collection.update_one(
            {"user_id": data["user_id"]},
            {"$set": {
                "username": data["username"],
                "server_nickname": data["server_nickname"],
                "joined_at_server": data["joined_at_server"],
                "granted_role": data["granted_role"],
            }},
            upsert=True
        )
        log_db("DB", f"User info synced: {data['username'], data['server_nickname']}", log_id=log_id)
    except Exception as e:
        log_db("Error", f"User info sync failed: {e}", log_id=log_id)

# Get User Information From DB
async def get_user_profile(user_id: str, log_id: str | None = None):
    doc = await collection.find_one({"user_id": user_id})
    log_db("DB", f"User profile doc: {doc}", log_id=log_id)
    return doc

# MongoDB 접속 테스트 함수
# async def test_mongo_connection():
#     try:
#         result = await db.command({"ping": 1})
#         print("✅ MongoDB 접속 성공:", result)
#     except Exception as e:
#         print("❌ MongoDB 접속 실패:", e)

# if __name__ == "__main__":
#     asyncio.run(test_mongo_connection())
