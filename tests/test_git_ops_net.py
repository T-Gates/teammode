"""이슈 #33/#34 — git_ops 네트워크 타임아웃 분리 + no-upstream push 자동 복구 테스트.

#33: DEFAULT_TIMEOUT=2s 가 실 GitHub SSH 왕복(~2.5s+)을 죽였다. 네트워크 동사
(pull/fetch/push 를 포함하는 함수)는 NET_TIMEOUT 을 기본값으로 쓰고, 순수 로컬
동사(rev-list·log·status 류)는 세션 시작 스냅함을 위해 DEFAULT_TIMEOUT 을 유지한다.

#34: upstream 미설정 브랜치에서 평문 `git push` 는 영원히 실패한다. do_commit 의
push 단계가 no-upstream 서명을 감지하면 `push -u origin HEAD` 로 1회 재시도한다.

네트워크는 /tmp 로컬 fake remote(bare) 로 모사 — 실 원격·실 ~/.claude 무접촉.
"""
import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "infra"))

import git_ops  # noqa: E402


# ──────────────────────────────────────────────────────────────────
# #33 — NET_TIMEOUT 상수 + 함수별 기본값 재분류
# ──────────────────────────────────────────────────────────────────

def test_net_timeout_exists_and_exceeds_default():
    assert hasattr(git_ops, "NET_TIMEOUT")
    assert git_ops.NET_TIMEOUT > git_ops.DEFAULT_TIMEOUT
    assert git_ops.NET_TIMEOUT == 10


def _timeout_default(func):
    return inspect.signature(func).parameters["timeout"].default


@pytest.mark.parametrize("name", [
    "do_pull",            # git pull — 네트워크
    "do_reconcile",       # 내부 fetch — 네트워크
    "do_commit",          # push + non-ff 복구 fetch/재push — 네트워크
    "fetch_upstream",     # git fetch — 네트워크
    "sync_from_upstream",  # 내부 fetch_upstream — 네트워크
])
def test_network_verbs_default_to_net_timeout(name):
    assert _timeout_default(getattr(git_ops, name)) == git_ops.NET_TIMEOUT


@pytest.mark.parametrize("name", [
    "ahead_behind",           # rev-list — 로컬
    "has_common_ancestor",    # merge-base — 로컬
    "count_behind",           # rev-list — 로컬
    "upstream_changes",       # log — 로컬
    "detect_default_branch",  # symbolic-ref/rev-parse — 로컬
    "diff_paths",             # diff — 로컬
    "read_upstream_notice",   # show(로컬 remote-tracking ref) — 로컬
])
def test_local_verbs_stay_at_default_timeout(name):
    assert _timeout_default(getattr(git_ops, name)) == git_ops.DEFAULT_TIMEOUT
