import sys
import os
import json
import subprocess

# 표준 입력(stdin) 및 출력(stdout) 인코딩을 UTF-8로 설정
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding='utf-8')
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')

# Core 순수 판정 로직 임포트 및 Facade 재노출 (하위 호환성 100% 유지)
cur_script_dir = os.path.dirname(os.path.abspath(__file__))
if cur_script_dir not in sys.path:
    sys.path.insert(0, cur_script_dir)

try:
    from core.stop_gate.test_gate_core import (
        DEFAULT_DOC_EXTS,
        is_only_doc_changes,
        parse_git_numstat_for_deletions,
        format_test_mutation_reason,
        resolve_test_runner_command,
        filter_violating_line_limit_files,
        format_line_limit_violation_reason,
        format_test_failure_reason,
        extract_dirty_source_files,
        check_architecture_line_limits,
        handle_test_failure_orchestration,
        reset_circuit_breaker,
        evaluate_test_mutation_by_policy,
        handle_test_mutation_gate,
        resolve_fallback_single_runner,
        cleanup_change_token,
        should_cleanup_change_token,
        finalize_gate,
    )
except ImportError:
    from .core.stop_gate.test_gate_core import (
        DEFAULT_DOC_EXTS,
        is_only_doc_changes,
        parse_git_numstat_for_deletions,
        format_test_mutation_reason,
        resolve_test_runner_command,
        filter_violating_line_limit_files,
        format_line_limit_violation_reason,
        format_test_failure_reason,
        extract_dirty_source_files,
        check_architecture_line_limits,
        handle_test_failure_orchestration,
        reset_circuit_breaker,
        evaluate_test_mutation_by_policy,
        handle_test_mutation_gate,
        resolve_fallback_single_runner,
        cleanup_change_token,
        should_cleanup_change_token,
        finalize_gate,
    )


from shell.pre_tool.pre_tool_shell import safe_read_stdin



def main():
    # Antigravity 런타임에서 stdin으로 전달되는 시스템 메타데이터 안전 수신 (블로킹 0%)
    payload = safe_read_stdin()

    # 워크스페이스 루트 경로 계산
    current_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_paths = payload.get("workspacePaths", [])
    if workspace_paths and os.path.exists(workspace_paths[0]):
        project_root = workspace_paths[0]
    else:
        # hooks.json의 위치(.agents)의 상위 폴더를 루트로 간주
        project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

    # [중앙 관제 설정 로드]: 최우선 로드
    config_file = os.path.join(current_dir, "..", "guard_config.json")
    check_test_deletion = True
    cdata = {}
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as cf:
                cdata = json.load(cf)
            check_test_deletion = cdata.get("switches", {}).get("prevent_test_deletion", True)
        except Exception:
            pass

    # =========================================================================
    # [1단계: 상시 정적 안전망 (0.01초 소요, 무조건 100% 실행)]
    # 변경 파일 종류(문서 여부)나 테스트 러너 유무와 무관하게 턴 종료 시 무조건 실행
    # =========================================================================
    if cdata:
        # 1-1. 3대 급소 O(1) 해시 무결성 감찰 게이트 (verify_hash_immutability - Core 위임)
        try:
            from core.common.hash_guard_core import run_hash_integrity_gate
            is_hash_pass, hash_err_msg = run_hash_integrity_gate(project_root, cdata)
            if not is_hash_pass:
                print(json.dumps({"decision": "continue", "reason": hash_err_msg}, ensure_ascii=False))
                return
        except Exception:
            pass

        # 1-2. 300줄 초과 감찰 게이트 (architecture_policy - Pure Core 위임)
        try:
            is_limit_pass, limit_reason = check_architecture_line_limits(project_root, cdata)
            if not is_limit_pass:
                print(json.dumps({"decision": "continue", "reason": limit_reason}, ensure_ascii=False))
                return
        except Exception:
            pass

    # [2단계: 변경 파일 수집 및 스마트 패스 (문서 변경 시 러너 스킵)]
    changed_files = []
    deleted_mutations = []
    try:
        st_proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if st_proc.returncode == 0 and st_proc.stdout.strip():
            for line in st_proc.stdout.splitlines():
                parts = line.strip().split(maxsplit=1)
                if len(parts) >= 2:
                    changed_files.append(parts[1].strip('"\' '))

        # 작업 트리가 깨끗하면(코드 변경 없는 단순 대화/질문 턴) 무거운 테스트 러너 스킵 및 단일 출구로 정상 종료
        if not changed_files:
            finalize_gate("allow", project_root=project_root, deleted_mutations=[])
            return

        # 1단계 정적 가드를 통과한 상태에서 순수 비코드만 변경된 경우 무거운 테스트 러너 스킵 후 정상 종료
        if is_only_doc_changes(changed_files):
            finalize_gate("allow", project_root=project_root, deleted_mutations=[])
            return
    except Exception:
        pass

    if check_test_deletion:
        try:
            diff_proc = subprocess.run(
                ["git", "diff", "--numstat", "HEAD", "--", "tests/"],
                cwd=project_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            if diff_proc.returncode == 0 and diff_proc.stdout.strip():
                deleted_mutations = parse_git_numstat_for_deletions(diff_proc.stdout)
                if deleted_mutations:
                    is_allowed, reason = handle_test_mutation_gate(
                        project_root=project_root,
                        deleted_mutations=deleted_mutations,
                        changed_files=changed_files,
                        guard_config=cdata
                    )
                    if not is_allowed:
                        print(json.dumps({"decision": "continue", "reason": reason}, ensure_ascii=False))
                        return
        except Exception:
            pass

    # 3. 다중 스택 및 서브프로젝트 러너 자동 판정 (스마트 멀티스택)
    multi_runners = []
    try:
        from core.common.stack_detector_core import resolve_multi_test_runners
        multi_runners = resolve_multi_test_runners(
            changed_files=changed_files,
            workspace_root=project_root,
            guard_config=cdata,
            is_win32=(sys.platform == "win32"),
            python_exe=sys.executable
        )
    except Exception:
        pass

    if not multi_runners:
        multi_runners = resolve_fallback_single_runner(
            project_root=project_root,
            is_win32=(sys.platform == "win32"),
            python_exe=sys.executable
        )

    # 테스트 대상이 아직 없는 초기 환경인 경우 정상 종료 승인 (단일 출구)
    if not multi_runners:
        finalize_gate("allow", project_root=project_root, deleted_mutations=[])
        return

    # 감지된 모든 스택/서브프로젝트 테스트 연쇄 실행 (All Pass 강제)
    for runner in multi_runners:
        runner_name = runner["name"]
        test_cmd = runner["cmd"]
        runner_cwd = runner.get("cwd", project_root)
        use_shell = runner.get("use_shell", False)

        try:
            proc = subprocess.run(
                test_cmd,
                cwd=runner_cwd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
                shell=use_shell
            )
        except subprocess.TimeoutExpired:
            response = {
                "decision": "continue",
                "reason": f"[테스트 게이트 차단] {runner_name} 실행 시간이 초과되었습니다 (60초 제한). 무한 루프 또는 데드락을 점검하세요."
            }
            print(json.dumps(response, ensure_ascii=False))
            return
        except Exception:
            # 도구 미설치 등 예상치 못한 실행 에러 시 작업 먹통 방지를 위한 Fallback
            continue

        if proc.returncode != 0:
            full_out = (proc.stdout + "\n" + proc.stderr).strip()
            failure_reason = handle_test_failure_orchestration(
                project_root=project_root,
                runner_name=runner_name,
                returncode=proc.returncode,
                stdout_and_stderr=full_out,
                changed_files=changed_files,
                guard_config=cdata,
                extract_dirty_sources_fn=extract_dirty_source_files
            )
            print(json.dumps({"decision": "continue", "reason": failure_reason}, ensure_ascii=False))
            return

    # 4. 모든 테스트 100% 통과 직후 4대 작업 유형별 Git Diff 무결성 및 유실 감찰 체인 실행
    diff_guard_script = os.path.join(current_dir, "shell", "stop_gate", "diff_guard.py")
    if os.path.exists(diff_guard_script):
        try:
            dg_proc = subprocess.run(
                [sys.executable, diff_guard_script],
                cwd=project_root,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            if dg_proc.returncode != 0:
                diff_err_msg = (dg_proc.stderr or dg_proc.stdout).strip()
                response = {
                    "decision": "continue",
                    "reason": (
                        f"[Diff Guard 차단: 데이터 유실/무결성 위반 감지]\n{diff_err_msg}\n"
                        "철칙: 성우/식별자 데이터 누락, 날림 주석(// 기존 코드 동일 등)을 원상 복구하세요.\n"
                        "[직언 가이드]: 비즈니스 코드가 정상인데 훅의 오탐/버그로 판단될 경우, 임의 우회하지 말고 즉시 사장님께 [훅 오탐 분석 및 수리 직언 보고]를 올리세요."
                    )
                }
                print(json.dumps(response, ensure_ascii=False))
                return
        except Exception:
            pass

    # 100% 통과 시 서킷 브레이커 카운터 즉시 리셋
    reset_circuit_breaker(os.path.join(project_root, ".agents"))

    # [단일 관문 종료]: should_cleanup_change_token 대조 후 안전한 토큰 자폭 및 최종 통과
    finalize_gate("allow", project_root=project_root, deleted_mutations=deleted_mutations)


if __name__ == "__main__":
    main()

