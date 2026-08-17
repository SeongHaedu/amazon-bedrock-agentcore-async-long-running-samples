import asyncio
import json
import logging
from typing import Dict, Any
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp, PingStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


@tool
def long_analysis(data_source: str, duration: int = 300) -> str:
    """長時間のデータ分析を実行する。"""
    import time
    logger.info(f"Starting analysis on {data_source}, estimated {duration}s")
    time.sleep(duration)
    return f"Analysis of {data_source} completed after {duration}s"


agent = Agent(
    model=BedrockModel(model_id="us.anthropic.claude-sonnet-4-20250514-v1:0"),
    tools=[long_analysis],
    system_prompt="You are a data analysis agent. Use the long_analysis tool when asked to analyze data.",
)


async def _background_run(task_id: int, payload: Dict[str, Any]):
    """バックグラウンドで非同期ジョブを実行する。"""
    try:
        job_id = payload.get("job_id", "default")
        user_input = payload.get("prompt", "")
        logger.info(f"[Background] task_id={task_id}, job_id={job_id} | start")

        response = await asyncio.to_thread(agent, user_input)
        result_text = response.message["content"][0]["text"]

        logger.info(f"[Background] task_id={task_id}, job_id={job_id} | completed: {result_text[:100]}")
    except Exception as e:
        logger.exception(f"[Background] task_id={task_id} | failed: {e}")
    finally:
        app.complete_async_task(task_id)


@app.ping
def health_check() -> PingStatus:
    """ヘルスチェック: アクティブなタスクがあれば HealthyBusy を返す。"""
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
    logger.info(f"[Entrypoint] session={session_id}, job_id={job_id}")

    if data.get("action") == "start":
        task_id = app.add_async_task("agent_job", {"job_id": job_id})
        asyncio.create_task(_background_run(task_id, data))
        return {"status": "started", "task_id": task_id}
    return {"status": "complete"}


if __name__ == "__main__":
    app.run()
