"""Synthetic C2B webhook load profile; use only against a disposable environment."""
from datetime import datetime, timezone
from itertools import count

from locust import HttpUser, between, task

_sequence = count(1)


class SyntheticC2BCallbackUser(HttpUser):
    wait_time = between(0.05, 0.5)

    @task
    def post_c2b_confirmation(self):
        sequence = next(_sequence)
        now = datetime.now(timezone.utc)
        payload = {
            "TransID": f"LOAD-{now:%Y%m%d%H%M%S}-{sequence}",
            "TransAmount": "10",
            "MSISDN": "254712345678",
            "TransTime": now.strftime("%Y%m%d%H%M%S"),
            "AccountReference": "SYNTHETIC-LOAD-TEST",
        }
        with self.client.post(
            "/webhook/c2b/confirmation",
            json=payload,
            name="/webhook/c2b/confirmation",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"callback returned HTTP {response.status_code}")
                return
            body = response.json()
            if body.get("ResultCode") != 0:
                response.failure("callback was not durably accepted")
            else:
                response.success()
