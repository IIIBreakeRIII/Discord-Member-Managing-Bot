### `.env` 파일의 구성

```python
# Discord Bot Token
DISCORD_BOT_TOKEN=[Enter Token Here]

# MongoDB URI
MONGODB_URI=[Enter MongoDB URI Here]

# 새로운 멤버에게 부여할 역할 이름 입력
MEMBER_ROLE_NAME=Member
GUEST_ROLE_NAME=Guest

# 메시지 ID (/멤버-공지메시지ID, /게스트-공지메시지ID)
MEMBER_NOTICE_MESSAGE_ID=[Enter Message ID Here]
GUEST_NOTICE_MESSAGE_ID=[Enter Message ID Here]

# 기타 설정값 (필요시 확장)
```

### `.config.json` 파일의 구성

```json
{
    "MEMBER_NOTICE_MESSAGE_ID": "1111111111111111111",
    "GUEST_NOTICE_MESSAGE_ID": "1111111111111111111"
}
```