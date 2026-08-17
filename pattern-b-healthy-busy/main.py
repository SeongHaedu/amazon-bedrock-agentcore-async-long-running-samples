import asyncio
import json
import logging
from typing import Dict, Any
from bedrock_agentcore.runtime import BedrockAgentCoreApp, PingStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


async def _background_run(task_id: int, payload: Dict[str, Any]):
    """バックグラウンドで長時間処理を実行するコルーチン。"""
    try:
        job_id = payload.get("job_id", "default")
        duration = payload.get("duration", 1200)
        logger.info(f"[Background] task_id={task_id}, job_id={job_id}, duration={duration}s | start")
        for elapsed in range(60, duration + 1, 60):
            await asyncio.sleep(60)
            logger.info(f"[Background] job_id={job_id} | elapsed={elapsed}s")
        remaining = duration % 60
        if remaining > 0:
            await asyncio.sleep(remaining)
        logger.info(f"[Background] task_id={task_id}, job_id={job_id} | completed in {duration}s")
    except Exception as e:
        logger.exception(f"[Background] task_id={task_id} | failed: {e}")
    finally:
        app.complete_async_task(task_id)


@app.ping
def health_check() -> PingStatus:
    """ヘルスチェック: アクティブタスクがあれば HealthyBusy を返す。"""
    task_info = app.get_async_task_info()
    active = task_info["active_count"]
    status = PingStatus.HEALTHY_BUSY if active > 0 else PingStatus.HEALTHY
    logger.info(f"Ping: status={status.value}, active_tasks={active}")
    return status


@app.entrypoint
async def invoke(payload: Dict[str, Any], context=None):
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
        task_id = app.add_async_task("long_job", {"job_id": job_id})
        asyncio.create_task(_background_run(task_id, data))
        return {"status": "started_with_busy", "task_id": task_id, "duration": data.get("duration", 1200)}
    elif action == "taskinfo":
        task_info = app.get_async_task_info()
        return {"active_count": task_info["active_count"], "running_jobs": task_info.get("tasks", [])}
    elif action == "whoami":
        with open("/proc/uptime") as f:
            uptime = f.read().strip()
        return {"status": "whoami", "uptime": uptime}
    return {"status": "complete"}


if __name__ == "__main__":
    app.run()
