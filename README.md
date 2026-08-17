# Amazon Bedrock AgentCore Runtime: 非同期 / 長時間実行エージェントのサンプル実装

Amazon Bedrock AgentCore Runtime で 15 分の Request timeout を超える長時間処理を実現するサンプルコードです。`add_async_task()` / `complete_async_task()` による HealthyBusy 制御の有無で、セッションのライフサイクルがどう変わるかを 3 パターンで示します。

![AgentCore Runtime session lifecycle](./images/session_lifecycle.png)

解説記事: [Amazon Bedrock AgentCore Runtime で実現する 非同期 / 長期実行エージェント](https://zenn.dev/ykbone/articles/agentcore-async-long-running-patterns)

## 構成

```
.
├── pattern-a-healthy-only/     対照実験: /ping が常に Healthy を返す (セッションは idle timeout で terminate)
│   └── main.py
├── pattern-b-healthy-busy/     推奨パターン: add_async_task で HealthyBusy を制御 (セッション維持)
│   └── main.py
├── pattern-c-strands-agent/    実践パターン: Strands Agents + HealthyBusy
│   ├── main.py
│   └── Dockerfile
├── Dockerfile                  共通 Dockerfile (pattern-a, pattern-b 用)
└── invoke.py                   invoke ヘルパースクリプト
```

| パターン | HealthyBusy | 結果 |
|---------|-------------|------|
| A | なし | `idleRuntimeSessionTimeout` でセッション terminate |
| B | あり | `maxLifetime` まで処理が継続 |
| C | あり + Strands Agent | AI エージェントの長時間 tool 呼び出しに対応 |

## 前提条件

- AWS CLI v2
- Python 3.13+
- Docker (ARM64 ビルド用に `docker buildx`)
- ECR リポジトリ (事前作成)

## デプロイ

```bash
# ECR ログイン
aws ecr get-login-password --region us-west-2 \
  | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com

# ビルド & push (pattern-b の例)
cd pattern-b-healthy-busy
docker buildx build --platform linux/arm64 \
  -t <account-id>.dkr.ecr.us-west-2.amazonaws.com/<repository-name>:pattern-b \
  -f ../Dockerfile --push .

# Runtime microVM でデプロイ
aws bedrock-agentcore-control create-agent-runtime \
  --region us-west-2 \
  --agent-runtime-name "async_long_running_pattern_b" \
  --role-arn "arn:aws:iam::<account-id>:role/<execution-role>" \
  --agent-runtime-artifact '{"containerConfiguration": {"containerUri": "<account-id>.dkr.ecr.us-west-2.amazonaws.com/<repository-name>:pattern-b"}}' \
  --protocol-configuration '{"serverProtocol": "HTTP"}' \
  --network-configuration '{"networkMode": "PUBLIC"}' \
  --lifecycle-configuration '{"idleRuntimeSessionTimeout": 1200, "maxLifetime": 28800}'
```

## 実行

```bash
# ジョブ開始
python invoke.py \
  --runtime-arn "arn:aws:bedrock-agentcore:us-west-2:<account-id>:runtime/<runtime-id>" \
  --session-id "longrun-session-min-33-characters-0001" \
  --action start \
  --duration 1300

# タスク状態確認 (pattern-b のみ)
python invoke.py \
  --runtime-arn "..." \
  --session-id "longrun-session-min-33-characters-0001" \
  --action taskinfo

# セッション生存確認
python invoke.py \
  --runtime-arn "..." \
  --session-id "longrun-session-min-33-characters-0001" \
  --action whoami
```

## 参考

- [Handle asynchronous and long running agents with Amazon Bedrock AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-long-run.html)
- [Runtime sessions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-sessions.html)
- [bedrock-agentcore-sdk-python (GitHub)](https://github.com/aws/bedrock-agentcore-sdk-python)
