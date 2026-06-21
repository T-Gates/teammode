# teammode SPEC

teammode SPEC v0.2 — 인덱스

spec_version: **0.2**

단일 권위본은 이 폴더(`docs/spec/`)입니다.

## L2 설계 상태 (2026-06-21)

L2 서비스 연결 방향은 `docs/BACKLOG.md`의 "L2 재설계 — 표준 인터페이스→표준 툴셋"
결정이 우선입니다. 새 방향은 `role_server + handlers + 역할 추상화`가 아니라,
Claude/Codex 등 벤더별 MCP 등록기에 provider MCP를 직접 등록하고 스킬이 표준 툴셋을
사용하는 방식입니다.

따라서 `handlers.md`와 `infra/mcp/role_server.py`는 v0.2 이전 모델의 legacy 문서/코드입니다.
새 Codex 배선이나 L2 기능은 이 경로 위에 새 투자를 하지 않습니다.

- [개요](00-overview.md) — §0 개요·용어·표기·버저닝.
- [설치 · 부트스트랩](onboarding.md) — §4 설치·부트스트랩.
- [온보딩 스킬](skills.md) — §5 tm-onboard·tm-connect.
- [내부 규범](internals.md) — §1 메모리, §2 훅·어댑터, §3 엔진 동사, §6 conformance, §7 provider, 부록 A~D.
