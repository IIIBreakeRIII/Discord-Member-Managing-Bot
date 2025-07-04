from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone
from pytz import timezone as pytz_timezone 

import os
# import asyncio

load_dotenv()
MONGO_URI = os.getenv("MONGODB_URI")

client = AsyncIOMotorClient(MONGO_URI)

db = client.watchersdb
collection = db.userlogs

# Formatting timezone to KR(Seoul) -> To Database
def format_kst(dt: datetime) -> str:
    kst = pytz_timezone("Asia/Seoul")
    return dt.astimezone(kst).strftime("%Y-%m-%dT%H-%M-%S")

# Formatting timezone to KR(Seoul) -> To User
def format_korean_datetime_string(dt_str: str) -> str:
    """
    'YYYY-MM-DDTHH-MM-SS' 형식 문자열을 'YYYY년 MM월 DD일 HH시MM분 SS초'로 변환
    """
    dt = datetime.strptime(dt_str, "%Y-%m-%dT%H-%M-%S")
    return f"{dt.year}년 {dt.month:02d}월 {dt.day:02d}일 {dt.hour:02d}시 {dt.minute:02d}분 {dt.second:02d}초"

# Update User Voice Log In DB
async def update_user_voice_log(user_id: str, username:str = None, join_time: datetime = None, leave_time: datetime = None, channel: str = None):
    update_fields = {}

    if join_time:
        update_fields["join_time"] = format_kst(join_time)
        update_fields["last_active"] = format_kst(join_time)

    if leave_time:
        update_fields["leave_time"] = format_kst(leave_time)

    if channel:
        update_fields["channel"] = channel

    if username:
        update_fields["username"] = username

    if not update_fields:
        print("❗ update_user_voice_log: update_fields 비어있음 — DB 쓰기 안 함")
        return

    print("📤 MongoDB 쓰기 시도 중:", update_fields)

    try:
        result = await collection.update_one(
            {"user_id": user_id},
            {"$set": update_fields},
            upsert=True
        )
        print("✅ MongoDB 쓰기 결과:", result.raw_result)
    except Exception as e:
        print("❌ MongoDB 쓰기 실패:", e)

# Get Last Active Time -> To User
async def get_last_active_by_user_id(user_id: str) -> str | None:
    doc = await collection.find_one({"user_id": user_id})
    print(doc)
    if doc and "last_active" in doc:
        return doc["last_active"]
    return None

# Save Role in DB
async def save_granted_role(user_id: str, username: str, role_name: str):
    doc = {
        "user_id": user_id,
        "username": username,
        "granted_role": role_name,
        "granted_time": format_kst(datetime.now(timezone.utc)),
    }

    print(f"📥 권한 부여 기록 저장 중: {doc}")
    
    try:
        await collection.update_one(
            {"user_id": user_id},
            {"$set": doc},
            upsert=True
        )
    except Exception as e:
        print("❌ MongoDB 저장 실패:", e)

# Save User's Server Enter Time in DB
async def save_join_time(user_id: str, username: str):
    doc = { "user_id": user_id, "username": username , "joined_at_server": format_kst(datetime.now(timezone.utc)), }
    
    print(f"📥 서버 입장 기록 저장 중: {doc}")

    try:
        await collection.update_one(
            {"user_id": user_id},
            {"$setOnInsert": doc},
            upsert=True
        )
    except Exception as e:
        print("❌ MongoDB 서버 입장 저장 실패:", e)

# User Voice Duration Time
async def get_total_voice_duration(user_id: str) -> int:
    """
    MongoDB에서 해당 유저의 전체 접속 시간 누적을 초 단위로 반환
    """
    doc = await collection.find_one({"user_id": user_id})
    if doc and "durations" in doc:
        return int(doc["durations"].get("total_seconds", 0))
    return 0

async def add_voice_duration(user_id: str, username: str, duration_seconds: int):
    try:
        await collection.update_one(
            {"user_id": user_id},
            {
                "$set": {"username": username},
                "$inc": {"durations.total_seconds": duration_seconds}
            },
            upsert=True
        )
        print(f"📈 {username} - {duration_seconds}초 누적 완료")
    except Exception as e:
        print(f"❌ 음성 체류 시간 누적 실패: {e}")

# Server Synchronization to DB
async def upsert_member_info(data: dict):
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
        print(f"🗂️  유저 정보 동기화됨: {data['username'], data['server_nickname']}")
    except Exception as e:
        print(f"❌ 유저 정보 동기화 실패: {e}")

# Get User Information From DB
async def get_user_profile(user_id: str):
    return await collection.find_one({"user_id": user_id})

# MongoDB 접속 테스트 함수
# async def test_mongo_connection():
#     try:
#         result = await db.command({"ping": 1})
#         print("✅ MongoDB 접속 성공:", result)
#     except Exception as e:
#         print("❌ MongoDB 접속 실패:", e)

# if __name__ == "__main__":
#     asyncio.run(test_mongo_connection())