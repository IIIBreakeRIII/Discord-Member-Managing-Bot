from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from datetime import datetime, timezone
from pytz import timezone as pytz_timezone

import os

load_dotenv()
MONGO_URI = os.getenv("MONGODB_URI")

client = AsyncIOMotorClient(MONGO_URI)
db = client.watchersdb
userlogs = db.userlogs
quitlogs = db.quitlogs

def format_kst(dt: datetime) -> str:
    kst = pytz_timezone("Asia/Seoul")
    return dt.astimezone(kst).strftime("%Y-%m-%dT%H-%M-%S")
        
async def move_user_to_quitlogs(user_id: str):
    # 1) userlogs에서 유저 정보 꺼내오기
    user_doc = await userlogs.find_one({"user_id": user_id})
    if not user_doc:
        print(f"❗ {user_id}의 정보를 userlogs에서 찾을 수 없음")
        return

    # 2) 불필요한 필드 삭제 (_id, user_id, 그리고 혹시 남아있을 times)
    user_doc.pop("_id", None)
    user_doc.pop("user_id", None)
    user_doc.pop("times", None)

    # 3) 퇴장 시각만 별도로 계산
    quit_time = format_kst(datetime.now(timezone.utc))

    # 4) quitlogs에 upsert: 필드는 $set으로, 횟수 증가는 $inc로
    await quitlogs.update_one(
        {"user_id": user_id},
        {
            "$set": {**user_doc, "quit_time": quit_time},
            "$inc": {"times": 1}
        },
        upsert=True
    )

    # 5) userlogs에서 원본 문서 삭제
    await userlogs.delete_one({"user_id": user_id})

    print(f"✅ {user_id}의 정보를 quitlogs로 이동 및 퇴장 시간 기록 완료 (times +1)")