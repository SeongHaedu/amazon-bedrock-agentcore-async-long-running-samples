"""AgentCore Runtime invoke スクリプト。

Usage:
    python invoke.py --runtime-arn <ARN> --session-id <SESSION_ID> --action start
    python invoke.py --runtime-arn <ARN> --session-id <SESSION_ID> --action whoami
    python invoke.py --runtime-arn <ARN> --session-id <SESSION_ID> --action taskinfo
"""

import argparse
import boto3
import json
import time


def invoke_agent(runtime_arn: str, session_id: str, payload: dict) -> dict:
    client = boto3.client("bedrock-agentcore", region_name="us-west-2")

    start = time.time()
    response = client.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=session_id,
        qualifier="DEFAULT",
        payload=json.dumps(payload).encode(),
    )
    elapsed = time.time() - start

    body = b""
    for chunk in response.get("response", []):
        body += chunk if isinstance(chunk, bytes) else bytes(chunk)

    result = json.loads(body.decode()) if body else {}
    print(f"Elapsed: {elapsed:.2f}s")
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Invoke AgentCore Runtime")
    parser.add_argument("--runtime-arn", required=True, help="Agent Runtime ARN")
    parser.add_argument("--session-id", required=True, help="Runtime Session ID (33+ chars)")
    parser.add_argument("--action", default="start", help="Action: start, whoami, taskinfo")
    parser.add_argument("--job-id", default="test-001", help="Job ID")
    parser.add_argument("--duration", type=int, default=1200, help="Background job duration (seconds)")
    args = parser.parse_args()

    payload = {
        "action": args.action,
        "job_id": args.job_id,
        "duration": args.duration,
    }

    invoke_agent(args.runtime_arn, args.session_id, payload)


if __name__ == "__main__":
    main()
