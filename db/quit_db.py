from datetime import datetime, timezone

from db.connection import userlogs, quitlogs
from utils.logging_utils import log_db
        
async def move_user_to_quitlogs(user_id: str, log_id: str | None = None):
    # 1) userlogs에서 유저 정보 꺼내오기
    user_doc = await userlogs.find_one({"user_id": user_id})
    if not user_doc:
        log_db("Error", f"User not found in userlogs: {user_id}", log_id=log_id)
        return

    # 2) 불필요한 필드 삭제 (_id, user_id, 그리고 혹시 남아있을 times)
    user_doc.pop("_id", None)
    user_doc.pop("user_id", None)
    user_doc.pop("times", None)

    # 3) 퇴장 시각만 별도로 계산
    quit_time = datetime.now(timezone.utc).isoformat()

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

    log_db("DB", f"Moved user to quitlogs with quit_time recorded (times +1): {user_id}", log_id=log_id)
