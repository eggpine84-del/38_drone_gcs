# [파일명]: stack_detector_core.py | [용도] 스마트 멀티스택(Python + TS/Remotion) 자율 감지 순수 코어 (Pure Functional Core)
import os
import re
import json
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    from core.multistack_scanner_core import (
        collect_all_source_dirs,
        collect_all_test_dirs,
        scan_multistack_line_counts,
        check_multistack_test_deletion,
        is_test_file_for_stack,
    )
except ImportError:
    from .multistack_scanner_core import (
        collect_all_source_dirs,
        collect_all_test_dirs,
        scan_multistack_line_counts,
        check_multistack_test_deletion,
        is_test_file_for_stack,
    )

try:
    from core.tia_core import extract_scoped_test_dirs
except ImportError:
    from .tia_core import extract_scoped_test_dirs


def _make_project_info(
    stack: str,
    curr_dir: str,
    norm_root: str,
    has_pkg: bool = False,
    has_tsc: bool = False
) -> Dict[str, Any]:
    """프로젝트 메타데이터 딕셔너리를 일관되게 생성하는 순수 헬퍼 함수."""
    rel_cwd = os.path.relpath(curr_dir, norm_root).replace("\\", "/")
    return {
        "stack": stack,
        "abs_cwd": curr_dir,
        "rel_cwd": "" if rel_cwd == "." else rel_cwd,
        "has_package_json": has_pkg,
        "has_tsconfig": has_tsc,
        "manifest_dir": curr_dir
    }


def find_enclosing_project_info(
    target_file_path: str,
    workspace_root: str,
    max_depth: int = 10
) -> Dict[str, Any]:
    """수정 대상 파일 위치에서 상위로 역추적하여 가장 가까운 프로젝트 신분증을 탐색하는 순수 함수."""
    norm_file = os.path.abspath(target_file_path)
    norm_root = os.path.abspath(workspace_root)

    # 워크스페이스 경계 검증 (Path Traversal 차단)
    try:
        common = os.path.commonpath([norm_file, norm_root])
        if os.path.abspath(common) != norm_root:
            norm_file = os.path.join(norm_root, os.path.basename(norm_file))
    except Exception:
        norm_file = os.path.join(norm_root, os.path.basename(norm_file))

    curr_dir = os.path.dirname(norm_file) if os.path.isfile(norm_file) else norm_file

    # 계단식 상위 역추적 (Path-Bubbling)
    depth = 0
    while depth < max_depth:
        try:
            if os.path.abspath(os.path.commonpath([curr_dir, norm_root])) != norm_root:
                break
        except Exception:
            break

        has_pkg = os.path.exists(os.path.join(curr_dir, "package.json"))
        has_tsc = os.path.exists(os.path.join(curr_dir, "tsconfig.json"))
        has_cargo = os.path.exists(os.path.join(curr_dir, "Cargo.toml"))
        has_gomod = os.path.exists(os.path.join(curr_dir, "go.mod"))
        has_py_manifest = (
            os.path.exists(os.path.join(curr_dir, "pyproject.toml"))
            or os.path.exists(os.path.join(curr_dir, "requirements.txt"))
            or os.path.exists(os.path.join(curr_dir, "pytest.ini"))
        )

        # 1. TypeScript / JavaScript 감지
        if has_pkg or has_tsc:
            return _make_project_info("typescript", curr_dir, norm_root, has_pkg, has_tsc)
        # 2. Rust 감지
        if has_cargo:
            return _make_project_info("rust", curr_dir, norm_root)
        # 3. Go 감지
        if has_gomod:
            return _make_project_info("go", curr_dir, norm_root)
        # 4. Python 매니페스트 감지
        if has_py_manifest and curr_dir != norm_root:
            return _make_project_info("python", curr_dir, norm_root)

        if curr_dir == norm_root:
            break

        parent = os.path.dirname(curr_dir)
        if parent == curr_dir:
            break
        curr_dir = parent
        depth += 1

    # 5. 폴더 순회로 특정되지 않은 경우 파일 확장자 기반 폴백 판정
    _, ext = os.path.splitext(norm_file)
    ext_lower = ext.lower()
    if ext_lower in [".ts", ".tsx", ".js", ".jsx"]:
        return {
            "stack": "typescript",
            "abs_cwd": norm_root,
            "rel_cwd": "",
            "has_package_json": os.path.exists(os.path.join(norm_root, "package.json")),
            "has_tsconfig": os.path.exists(os.path.join(norm_root, "tsconfig.json")),
            "manifest_dir": norm_root
        }
    if ext_lower == ".go":
        return {
            "stack": "go",
            "abs_cwd": norm_root,
            "rel_cwd": "",
            "has_package_json": False,
            "has_tsconfig": False,
            "manifest_dir": norm_root
        }

    return {
        "stack": "python",
        "abs_cwd": norm_root,
        "rel_cwd": "",
        "has_package_json": False,
        "has_tsconfig": False,
        "manifest_dir": norm_root
    }


def resolve_multi_test_runners(
    changed_files: List[str],
    workspace_root: str,
    guard_config: Optional[Dict[str, Any]] = None,
    is_win32: bool = True,
    python_exe: str = "python"
) -> List[Dict[str, Any]]:
    """변경된 파일 목록을 분석하여 실행해야 하는 다중 언어 테스트 러너를 확정하는 순수 함수."""
    cfg = guard_config or {}
    custom_policy = cfg.get("test_runner_policy", {})
    runners: List[Dict[str, Any]] = []
    seen_runner_keys: Set[str] = set()

    # 사장님 명시 커스텀 정책(test_runner_policy) 우선 반영
    has_custom_policy = bool(custom_policy)
    remotion_runner = custom_policy.get("remotion_runner", "")
    remotion_cwd_rel = custom_policy.get("remotion_cwd", "remotion")
    python_runner = custom_policy.get("python_runner", "pytest")

    has_py_change = False
    has_ts_change = False
    has_go_change = False
    affected_projects: Dict[str, Dict[str, Any]] = {}

    for fpath in changed_files:
        norm_rel = fpath.replace("\\", "/").strip('"\' ')
        _, ext = os.path.splitext(norm_rel)
        ext_lower = ext.lower()

        if ext_lower == ".py":
            has_py_change = True
        elif ext_lower in [".ts", ".tsx", ".js", ".jsx"]:
            has_ts_change = True
        elif ext_lower == ".go":
            has_go_change = True

        abs_file = os.path.join(workspace_root, norm_rel)
        info = find_enclosing_project_info(abs_file, workspace_root)
        key = info["rel_cwd"]
        if key not in affected_projects:
            affected_projects[key] = info

    # 1. 사장님 명시 정책이 있는 경우 (하이브리드 호환)
    if has_custom_policy:
        if has_py_change:
            p_key = "py_custom"
            if p_key not in seen_runner_keys:
                seen_runner_keys.add(p_key)
                runners.append({
                    "name": f"python ({python_runner})",
                    "cmd": [python_exe, "-m", "pytest", "-q"] if python_runner == "pytest" else [python_runner],
                    "cwd": workspace_root,
                    "use_shell": False if python_runner == "pytest" else is_win32
                })

        if has_ts_change or any(remotion_cwd_rel in k for k in affected_projects):
            r_key = "remotion_custom"
            if r_key not in seen_runner_keys and remotion_runner:
                seen_runner_keys.add(r_key)
                target_cwd = os.path.join(workspace_root, remotion_cwd_rel)
                if not os.path.exists(target_cwd):
                    target_cwd = workspace_root
                runners.append({
                    "name": f"remotion ({remotion_runner})",
                    "cmd": remotion_runner.split(),
                    "cwd": target_cwd,
                    "use_shell": is_win32
                })
        return runners

    # 2. 미설정 시 완전 자율 감지 모드
    for rel_cwd, info in affected_projects.items():
        stack = info["stack"]
        proj_cwd = info["abs_cwd"]

        if stack == "python":
            r_key = f"py_{rel_cwd}"
            if r_key not in seen_runner_keys:
                seen_runner_keys.add(r_key)
                scoped_dirs, is_fallback = extract_scoped_test_dirs(changed_files)
                target_dirs = [d for d in scoped_dirs if os.path.exists(os.path.join(proj_cwd, d))] if (scoped_dirs and not is_fallback) else []
                cmd = [python_exe, "-m", "pytest", "-q"] + (target_dirs if target_dirs else [])
                runners.append({
                    "name": f"python (pytest) [{rel_cwd or 'root'}]",
                    "cmd": cmd,
                    "cwd": proj_cwd,
                    "use_shell": False
                })

        elif stack == "typescript":
            r_key = f"ts_{rel_cwd}"
            if r_key not in seen_runner_keys:
                seen_runner_keys.add(r_key)
                pkg_path = os.path.join(proj_cwd, "package.json")
                has_test = False
                if os.path.exists(pkg_path):
                    try:
                        with open(pkg_path, "r", encoding="utf-8") as pf:
                            has_test = bool(json.load(pf).get("scripts", {}).get("test"))
                    except Exception:
                        has_test = False

                runners.append({
                    "name": f"typescript ({'npm test' if has_test else 'tsc check'}) [{rel_cwd or 'root'}]",
                    "cmd": ["npm", "test"] if has_test else ["npx", "tsc", "--noEmit"],
                    "cwd": proj_cwd,
                    "use_shell": is_win32
                })

        elif stack == "go":
            r_key = f"go_{rel_cwd}"
            if r_key not in seen_runner_keys:
                seen_runner_keys.add(r_key)
                runners.append({
                    "name": f"go (go test) [{rel_cwd or 'root'}]",
                    "cmd": ["go", "test", "./..."],
                    "cwd": proj_cwd,
                    "use_shell": is_win32
                })

    # 변경 파일이 없거나 식별되지 않았을 때 폴백
    if not runners:
        if has_go_change or os.path.exists(os.path.join(workspace_root, "go.mod")):
            runners.append({
                "name": "go (go test) [fallback]",
                "cmd": ["go", "test", "./..."],
                "cwd": workspace_root,
                "use_shell": is_win32
            })
        elif has_py_change or os.path.exists(os.path.join(workspace_root, "tests")):
            runners.append({
                "name": "python (pytest) [fallback]",
                "cmd": [python_exe, "-m", "pytest", "-q"],
                "cwd": workspace_root,
                "use_shell": False
            })

    return runners


