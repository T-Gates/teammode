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


# ──────────────────────────────────────────────────────────────────
# #34 — no-upstream 브랜치 push 자동 복구(-u origin HEAD 1회 재시도)
# ──────────────────────────────────────────────────────────────────

def _git(cwd, *args, check=True):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        "GIT_TERMINAL_PROMPT": "0",
    }
    return subprocess.run(["git", "-C", str(cwd), *args],
                          capture_output=True, text=True, env=env, check=check)


@pytest.fixture
def new_branch_repo(tmp_path):
    """bare origin + clone, clone 은 upstream 없는 새 브랜치(feat/x) 체크아웃 상태."""
    origin = tmp_path / "origin.git"
    clone = tmp_path / "clone"
    _git(tmp_path, "init", "--bare", str(origin))
    _git(tmp_path, "clone", str(origin), str(clone))
    # do_commit(제품 코드)의 커밋은 _git 헬퍼 env 를 못 받는다 — CI 러너(글로벌 git
    # 설정 없음)에선 identity 자동감지가 fatal 이므로 레포 로컬 config 로 고정.
    _git(clone, "config", "user.name", "t")
    _git(clone, "config", "user.email", "t@t")
    (clone / "a.txt").write_text("v1\n")
    _git(clone, "add", ".")
    _git(clone, "commit", "-m", "c1")
    _git(clone, "branch", "-M", "main")
    _git(clone, "push", "-u", "origin", "main")
    # upstream 없는 새 브랜치 — 평문 `git push` 는 no-upstream 으로 거부된다.
    _git(clone, "checkout", "-b", "feat/x")
    return origin, clone


def test_do_commit_push_sets_upstream_on_new_branch(new_branch_repo):
    origin, clone = new_branch_repo
    (clone / "b.txt").write_text("v2\n")
    res = git_ops.do_commit(str(clone), "feat: b", push=True)
    assert res.ok is True
    assert res.committed is True
    assert res.pushed is True, res.detail
    # 원격(bare)에 feat/x 가 실제로 생겼는지
    rp = _git(origin, "rev-parse", "feat/x", check=False)
    assert rp.returncode == 0, rp.stderr
    # 재시도 경로(-u) 를 탔다는 표식
    assert "set upstream" in res.detail


def test_do_commit_second_push_uses_now_set_upstream(new_branch_repo):
    origin, clone = new_branch_repo
    (clone / "b.txt").write_text("v2\n")
    first = git_ops.do_commit(str(clone), "feat: b", push=True)
    assert first.pushed is True, first.detail
    # -u 재시도가 upstream 을 심었으므로 두 번째부턴 평문 push 가 그냥 성공한다.
    (clone / "c.txt").write_text("v3\n")
    second = git_ops.do_commit(str(clone), "feat: c", push=True)
    assert second.ok is True
    assert second.pushed is True, second.detail
    assert "set upstream" not in second.detail
    head = _git(clone, "rev-parse", "HEAD").stdout.strip()
    remote_head = _git(origin, "rev-parse", "feat/x").stdout.strip()
    assert head == remote_head
