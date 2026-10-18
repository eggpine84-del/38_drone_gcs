# -*- coding: utf-8 -*-
# [파일명]: pre_tool_guard.py | [용도] PreToolUse 도구 실행 전 실시간 3단계 보안 감찰관 훅
import sys
import os
import json
import subprocess

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

cur_script_dir = os.path.dirname(os.path.abspath(__file__))
if cur_script_dir not in sys.path:
    sys.path.insert(0, cur_script_dir)

from core.pre_tool.pre_tool_guard_core import (
    DEFAULT_GUARD_CONFIG,
    check_deploy_command,
    is_sanctuary_file,
    is_bypass_extension,
    check_overwrite_violation,
    check_test_deletion_violation,
    check_pin_test_requirement,
    is_test_file_for_stack,
    evaluate_multi_test_red_status,
    check_refactor_mode_eligibility,
    orchestrate_refactor_gate,
    safe_read_stdin,
)
from core.stop_gate.tia_core import run_targeted_partner_test
from core.pre_tool.ui_stack_guard_core import check_ui_stack_violation
from core.pre_tool.feature_boundary_core import check_cross_feature_import
from core.pre_tool.syntax_guard_core import check_python_syntax_pre_tool
from shell.stop_gate.universal_red_guard import verify_universal_red_failure
from core.pre_tool.red_cache_core import check_red_status_with_cache, is_red_cache_hit
from shell.pre_tool.pre_tool_shell import load_guard_config



def send_response(decision: str, reason: str = "") -> None:
    """판정 결과(allow/deny)를 stdout JSON으로 송신하고 즉시 종료."""
    payload = {"decision": decision}
    if reason:
        payload["reason"] = reason
    print(json.dumps(payload, ensure_ascii=False))
    sys.exit(0)


def get_git_status(project_root: str) -> list[str]:
    """Git 변경 파일 목록을 안전하게 수집하는 쉘 함수."""
    try:
        st_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3
        )
        if st_proc.returncode == 0 and st_proc.stdout.strip():
            changed = []
            for line in st_proc.stdout.splitlines():
                parts = line.strip().split(maxsplit=1)
                if len(parts) >= 2:
                    changed.append(parts[1].strip('"\' '))
            return changed
    except Exception:
        pass
    return []


def verify_test_red_failure(project_root: str, test_file: str) -> tuple[bool, str]:
    """신규 작성된 핀-테스트가 실제로 실패(Red)하는지 검증하는 실행기 (다국어 범용 검증 위임)."""
    return verify_universal_red_failure(project_root, test_file)


def main():
    payload = safe_read_stdin()

    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    workspace_paths = payload.get("workspacePaths", [])
    if workspace_paths and os.path.exists(workspace_paths[0]):
        project_root = workspace_paths[0]
    else:
        project_root = os.path.abspath(os.path.join(cur_script_dir, "..", ".."))

    guard_config = load_guard_config(project_root)
    switches = guard_config.get("switches", {})

    # 세션 시작 시점의 불변 대상 파일 베이스라인 캡처
    if switches.get("verify_hash_immutability", True):
        snap_path = os.path.join(project_root, ".agents", ".baseline_hashes.json")
        if not os.path.exists(snap_path):
            try:
                from core.common.hash_guard_core import save_baseline_snapshot, DEFAULT_HASH_POLICY
                from core.stop_gate.multistack_scanner_core import collect_all_test_dirs
                hp = guard_config.get("hash_guard_policy", DEFAULT_HASH_POLICY)
                extra_tests = collect_all_test_dirs(project_root)
                targets = set(hp.get("sanctuary_paths", []) + hp.get("refactor_immutable_dirs", []) + hp.get("fix_immutable_dirs", []) + extra_tests)
                save_baseline_snapshot(project_root, list(targets))
            except Exception:
                pass

    # [검문소 0]: 상용 배포 명령어 사전 승인 원천 차단
    if tool_name == "run_command":
        command_line = str(args.get("CommandLine", "")).strip()
        block_deploy = switches.get("block_unauthorized_deploy", True)

        token_path = os.path.join(project_root, ".agents", ".deploy_token")
        if os.path.exists(token_path):
            try:
                os.remove(token_path)
            except Exception:
                pass
            send_response("allow")

        blocked_cmds = guard_config.get("blocked_commands", ["git push", "vercel"])
        is_allowed, reason = check_deploy_command(command_line, blocked_cmds, block_deploy=block_deploy)
        if not is_allowed:
            send_response("deny", reason)
        send_response("allow")

    target_file = args.get("TargetFile", "")
    if not target_file:
        send_response("allow")

    target_abs = os.path.abspath(target_file)
    target_rel = os.path.relpath(target_abs, project_root)
    norm_rel = target_rel.replace("\\", "/")
    _, ext = os.path.splitext(target_abs)

    # [성역화 가드]: 중앙 관제 설정 파일 보호
    if switches.get("protect_sanctuary_files", True) and is_sanctuary_file(norm_rel):
        reason = (
            "[PreTool 차단: 중앙 조종석 성역화 보호]\n"
            f"대상 파일 '{target_rel}'은 사장님 전용 관제 설정 파일입니다.\n"
            "AI의 권한 상승 및 탈옥을 원천 차단하기 위해 도구를 통한 수정이 전면 금지되어 있습니다.\n"
            "설정 변경이 필요할 경우, 오직 사장님께서 직접 에디터에서 수정해 주셔야 합니다."
        )
        send_response("deny", reason)

    # 문서 및 정적 파일 스마트 패스
    bypass_exts = set(guard_config.get("bypass_extensions", [".md", ".txt", ".canvas"]))
    if is_bypass_extension(ext, bypass_exts):
        send_response("allow")

    # [검문소 1]: write_to_file 호출 시 덮어쓰기, UI스택, 피처 격리, 문법 감찰
    if tool_name == "write_to_file":
        is_allowed, reason = check_overwrite_violation(tool_name, os.path.exists(target_abs), target_rel)
        if not is_allowed:
            send_response("deny", reason)
        is_allowed, reason = check_ui_stack_violation(norm_rel, args.get("CodeContent", ""), guard_config)
        if not is_allowed:
            send_response("deny", reason)
        is_allowed, reason = check_cross_feature_import(norm_rel, args.get("CodeContent", ""), guard_config)
        if not is_allowed:
            send_response("deny", reason)
        is_ok, reason = check_python_syntax_pre_tool(
            norm_rel, tool_name, args, "", enable_check=switches.get("instant_syntax_check", True)
        )
        if not is_ok:
            send_response("deny", reason)
        send_response("allow")

    # [검문소 2]: replace_file_content 호출 시 감찰
    if tool_name in ["replace_file_content", "multi_replace_file_content"]:
        norm_rel = target_rel.replace("\\", "/")
        repl_code = args.get("ReplacementContent", "")
        if not repl_code and "ReplacementChunks" in args:
            repl_code = "\n".join(c.get("ReplacementContent", "") for c in args.get("ReplacementChunks", []))
        is_allowed, reason = check_ui_stack_violation(norm_rel, repl_code, guard_config)
        if not is_allowed:
            send_response("deny", reason)
        is_allowed, reason = check_cross_feature_import(norm_rel, repl_code, guard_config)
        if not is_allowed:
            send_response("deny", reason)

        # 실시간 문법 사전 감찰 (가상 패치 AST 검증)
        cur_content = ""
        if os.path.exists(target_abs):
            try:
                with open(target_abs, "r", encoding="utf-8", errors="replace") as f:
                    cur_content = f.read()
            except Exception:
                pass
        is_ok, reason = check_python_syntax_pre_tool(
            norm_rel, tool_name, args, cur_content, enable_check=switches.get("instant_syntax_check", True)
        )
        if not is_ok:
            send_response("deny", reason)

        # prevent_test_deletion 검문
        is_target_test = (
            (norm_rel.startswith("tests/") and norm_rel.endswith(".py"))
            or is_test_file_for_stack(norm_rel, "python")
            or is_test_file_for_stack(norm_rel, "typescript")
            or is_test_file_for_stack(norm_rel, "go")
        )
        if is_target_test:
            if switches.get("prevent_test_deletion", True) and os.path.exists(target_abs):
                try:
                    with open(target_abs, "r", encoding="utf-8", errors="ignore") as f:
                        old_code = f.read()
                    target_code = args.get("TargetContent", "")
                    replacement_code = args.get("ReplacementContent", "")
                    is_allowed, reason = check_test_deletion_violation(old_code, target_code, replacement_code, target_rel)
                    if not is_allowed:
                        send_response("deny", reason)
                except Exception:
                    pass
            send_response("allow")

        changed_files = get_git_status(project_root)
        if not changed_files and not os.path.exists(os.path.join(project_root, ".git")):
            send_response("allow")

        # 리팩토링 게이트
        is_candidate, is_ok, reason = orchestrate_refactor_gate(
            target_abs=target_abs,
            norm_rel=norm_rel,
            guard_config=guard_config,
            changed_files=changed_files,
            test_runner_fn=lambda: run_targeted_partner_test(norm_rel, project_root=project_root),
            work_mode=os.environ.get("GIT_WORK_MODE", "").strip().lower()
        )
        if is_candidate:
            if is_ok:
                send_response("allow")
            send_response("deny", reason)

        test_changes = []
        if switches.get("require_pin_test_first", True):
            has_root_src = os.path.exists(os.path.join(project_root, "src"))
            is_allowed, test_changes, reason = check_pin_test_requirement(norm_rel, changed_files, has_root_src=has_root_src)
            if not is_allowed:
                send_response("deny", reason)

        # 핀-테스트 Red 검증 (세션 캐시 및 os.path.getmtime 정렬 기반)
        if test_changes and switches.get("require_red_test_first", True):
            has_red, verified_test, reject_reason = check_red_status_with_cache(
                project_root=project_root,
                test_changes=test_changes,
                verifier_fn=lambda t: verify_universal_red_failure(project_root, t)
            )
            if not has_red:
                dirty_sources = [
                    f for f in changed_files
                    if not is_bypass_extension(os.path.splitext(f)[1].lower(), bypass_exts)
                    and not any(t in f.replace("\\", "/").lower() for t in ["tests/", "test_", "_test.", ".test."])
                ]
                restore_cmd = f"git restore {' '.join(dirty_sources)}" if dirty_sources else "git restore <대상파일>"
                guidance = (
                    "\n\n[자가치유 안내] (롤백 우선)"
                    f"\n1. 기존 코드 원복(롤백) 목적이라면: replace_file_content 대신 'run_command'로 '{restore_cmd}'를 실행하세요."
                    "\n2. 깨진 기존 테스트 수리 및 신규 검증 시: 기존 테스트 파일은 수정하지 말고, 'tests/test_pin_<기능명>.py' 신규 핀-테스트 파일을 생성하여 Red 실패 상태를 등록한 뒤 검증받으세요."
                )
                send_response("deny", reject_reason + guidance)

        send_response("allow")

    send_response("allow")


if __name__ == "__main__":
    main()
