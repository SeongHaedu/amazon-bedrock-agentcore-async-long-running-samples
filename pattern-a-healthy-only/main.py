import threading
import time
import json
import logging
from typing import Dict, Any
from bedrock_agentcore.runtime import BedrockAgentCoreApp, PingStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


def _background_run(payload: Dict[str, Any]):
    """バックグラウンドで長時間処理を実行する (HealthyBusy なし)。"""
    try:
        job_id = payload.get("job_id", "default")
        duration = payload.get("duration", 1300)
        logger.info(f"[Background] job_id={job_id}, duration={duration}s | start (no async task tracking)")
        for elapsed in range(60, duration + 1, 60):
            time.sleep(60)
            logger.info(f"[Background] job_id={job_id} | elapsed={elapsed}s")
        logger.info(f"[Background] job_id={job_id} | completed in {duration}s")
    except Exception as e:
        logger.exception(f"[Background] failed: {e}")


@app.ping
def health_check() -> PingStatus:
    """常に Healthy を返す (HealthyBusy に遷移しない)。"""
    return PingStatus.HEALTHY


@app.entrypoint
def invoke(payload: Dict[str, Any], context=None):
    """エントリーポイント: リクエストを受けて即座にレスポンスを返す。"""
    session_id = context.session_id if context else "local"

    raw = payload.get("prompt", "")
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            data = payload
    else:
        data = payload

    job_id = data.get("job_id", "default")
    action = data.get("action")
    logger.info(f"[Entrypoint] session={session_id}, job_id={job_id}, action={action}")

    if action == "start":
        threading.Thread(target=_background_run, args=(data,), daemon=True).start()
        return {"status": "started_without_busy", "duration": data.get("duration", 1300)}
    elif action == "whoami":
        with open("/proc/uptime") as f:
            uptime = f.read().strip()
        return {"status": "whoami", "uptime": uptime}
    return {"status": "complete"}


if __name__ == "__main__":
    app.run()
