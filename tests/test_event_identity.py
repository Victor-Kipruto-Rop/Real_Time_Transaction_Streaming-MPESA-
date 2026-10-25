# Database & Messaging
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1
pg8000==1.30.5
redis==5.0.1
aioredis==2.0.1
confluent-kafka==2.3.0
kafka-python==2.0.2



def test_b2c_result_identity_uses_nested_provider_conversation_id():
    first = {"Result": {"ConversationID": "AG_123", "ResultCode": 0}}
    retry = {"Result": {"ConversationID": "AG_123", "ResultCode": 1}}

    assert replay_key(first, "b2c_result") == replay_key(retry, "b2c_result")
