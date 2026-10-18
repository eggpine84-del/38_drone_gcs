# [파일명]: diff_guard.py | [용도] 4대 작업 유형별 Git Diff 무결성 및 데이터 유실 방지 자립형 가드
import sys
import os
import re
import json
import subprocess
from typing import Any

# 표준 입출력 UTF-8 강제
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# Core 순수 로직 임포트 및 Facade 재노출 (하위 호환성 100% 유지)
cur_script_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.abspath(os.path.join(cur_script_dir, "..", ".."))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)
if cur_script_dir not in sys.path:
    sys.path.insert(0, cur_script_dir)

try:
    from core.stop_gate.diff_guard_core import analyze_git_diff, _extract_identifiers, DEFAULT_POLICY
except ImportError:
    from .core.stop_gate.diff_guard_core import analyze_git_diff, _extract_identifiers, DEFAULT_POLICY
try:
    from core.stop_gate.test_mutation_core import resolve_work_mode
except ImportError:
    from .core.stop_gate.test_mutation_core import resolve_work_mode


def load_guard_config(project_root: str) -> dict:
    """중앙 관제 설정 로드 및 안전 폴백."""
    cfg_path = os.path.join(project_root, ".agents", "guard_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "switches": {"verify_git_diff_integrity": True},
        "diff_guard_policy": {
            "max_consecutive_deletions_in_feat": 15,
            "max_consecutive_deletions_in_change": 15,
            "max_consecutive_deletions_in_fix": 70,
            "protected_key_patterns": ["id", "key", "name", "code"],
            "banned_comment_patterns": ["기존 코드 동일", "기존코드동일", "unchanged", "TODO", "구현 예정", "..."]
        }
    }


def get_git_diff(project_root: str) -> str:
    """Git Diff 텍스트 수집 (스테이징 우선, 없으면 HEAD 기준)."""
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout

        proc_head = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5
        )
        if proc_head.returncode == 0 and proc_head.stdout.strip():
            return proc_head.stdout

        proc_plain = subprocess.run(
            ["git", "diff"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5
        )
        return proc_plain.stdout if proc_plain.returncode == 0 else ""
    except Exception:
        return ""


def detect_work_mode(project_root: str, cfg: dict) -> str:
    """작업 모드(feat, change, fix, refactor) 감지 (SSOT: test_mutation_core.resolve_work_mode 위임)."""
    return resolve_work_mode(project_root, guard_config=cfg)


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".."))

    cfg = load_guard_config(project_root)
    switches = cfg.get("switches", {})
    if not switches.get("verify_git_diff_integrity", True):
        sys.exit(0)

    diff_text = get_git_diff(project_root)
    if not diff_text.strip():
        sys.exit(0)

    mode = detect_work_mode(project_root, cfg)
    policy = cfg.get("diff_guard_policy", {})

    result = analyze_git_diff(diff_text, work_mode=mode, policy=policy)

    if result.get("decision") == "block":
        print("\n" + "=" * 70, file=sys.stderr)
        print("[Diff Guard 차단: 4대 작업 유형 Git Diff 무결성 위반 감지]", file=sys.stderr)
        print(f"현재 감지된 작업 모드: {mode}", file=sys.stderr)
        for v in result.get("violations", []):
            print(f" - [위반] {v}", file=sys.stderr)
        print(" [직언 가이드]: 비즈니스 코드가 정상인데 훅의 오탐/버그로 판단될 경우, 임의 우회하지 말고 즉시 사장님께 [훅 오탐 분석 및 수리 직언 보고]를 올리세요.", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
