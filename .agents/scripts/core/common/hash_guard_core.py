# [파일명]: hash_guard_core.py | [용도] 3대 급소 O(1) 해시 무결성 판정 순수 코어 (Pure Functional Core)
import os
import hashlib
from typing import Any

DEFAULT_HASH_POLICY: dict[str, Any] = {
    "sanctuary_paths": [
        ".agents/guard_config.json",
        ".agents/hooks.json",
        ".agents/scripts"
    ],
    "refactor_immutable_dirs": [
        "tests",
        "src/data"
    ],
    "fix_immutable_dirs": [
        "src/data"
    ]
}


def calculate_file_hash(file_path: str) -> str:
    """단일 파일의 SHA-256 해시를 결정론적으로 계산하는 순수 함수 (부재 시 빈 문자열 반환)."""
    if not file_path or not os.path.isfile(file_path):
        return ""
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


def _norm_path(p: str) -> str:
    """Windows/Linux 크로스 플랫폼 경로 정규화 (슬래시 통일)."""
    return os.path.normpath(p).replace("\\", "/")


def capture_directory_hashes(dir_rel: str, root_dir: str) -> dict[str, str]:
    """대상 디렉터리 내의 모든 파일에 대한 상대경로-해시 매핑을 생성하는 수집 함수."""
    result: dict[str, str] = {}
    target_abs = os.path.join(root_dir, dir_rel)
    if not os.path.exists(target_abs):
        return result

    if os.path.isfile(target_abs):
        norm_key = _norm_path(dir_rel)
        result[norm_key] = calculate_file_hash(target_abs)
        return result

    for root, _, files in os.walk(target_abs):
        if "__pycache__" in root or ".git" in root or ".pytest_cache" in root:
            continue
        for fname in files:
            if fname.endswith((".pyc", ".pyo", ".tmp")):
                continue
            abs_path = os.path.join(root, fname)
            rel_path = _norm_path(os.path.relpath(abs_path, root_dir))
            h = calculate_file_hash(abs_path)
            if h:
                result[rel_path] = h
    return result


def verify_hash_integrity(
    baseline: dict[str, str],
    current: dict[str, str],
    work_mode: str = "default",
    policy: dict[str, Any] | None = None
) -> dict[str, Any]:
    """기준 해시 맵과 현재 해시 맵을 비교하여 작업 모드별 불변성 위반 여부를 O(1)로 판정하는 순수 함수."""
    cfg = dict(DEFAULT_HASH_POLICY)
    if policy:
        cfg.update(policy)

    mode = (work_mode or "default").lower().strip()
    violations: list[str] = []

    # 크로스 플랫폼 일관성을 위해 베이스라인 및 현재 해시 키 정규화
    norm_baseline = {_norm_path(k): v for k, v in baseline.items()}
    norm_current = {_norm_path(k): v for k, v in current.items()}

    # 1. [공통 성역 검문]: sanctuary_paths 변조 여부 전수 대조
    sanctuary_prefixes = [_norm_path(p) for p in cfg.get("sanctuary_paths", [])]
    for rel_path, base_hash in norm_baseline.items():
        is_sanctuary = any(rel_path == sp or rel_path.startswith(sp + "/") for sp in sanctuary_prefixes)
        if not is_sanctuary:
            continue

        curr_hash = norm_current.get(rel_path, "")
        if curr_hash != base_hash:
            violations.append(
                f"[성역화 위반] 중앙 관제 파일 변조 감지 ('{rel_path}') - AI 권한 상승 및 탈옥 원천 차단"
            )

    # 2. [refactor 모드 검문]: refactor_immutable_dirs 불변 (Zero-Mutation)
    if mode == "refactor":
        refactor_dirs = [_norm_path(p) for p in cfg.get("refactor_immutable_dirs", [])]
        for rel_path, base_hash in norm_baseline.items():
            in_refactor_zone = any(rel_path == rd or rel_path.startswith(rd + "/") for rd in refactor_dirs)
            if not in_refactor_zone:
                continue

            curr_hash = norm_current.get(rel_path, "")
            if curr_hash != base_hash:
                violations.append(
                    f"[리팩토링 위반] Zero-Mutation 위반 감지 ('{rel_path}') - 리팩토링 중 테스트 및 데이터 파일 변경 불허"
                )

    # 3. [fix 모드 검문]: fix_immutable_dirs 데이터 파일 변조 금지
    if mode == "fix":
        fix_dirs = [_norm_path(p) for p in cfg.get("fix_immutable_dirs", [])]
        for rel_path, base_hash in norm_baseline.items():
            in_fix_zone = any(rel_path == fd or rel_path.startswith(fd + "/") for fd in fix_dirs)
            if not in_fix_zone:
                continue

            curr_hash = norm_current.get(rel_path, "")
            if curr_hash != base_hash:
                violations.append(
                    f"[디버그 위반] 데이터 조작 의심 감지 ('{rel_path}') - 데이터 변조를 통한 결함 덮기 원천 차단"
                )

    if violations:
        return {
            "decision": "block",
            "violations": violations,
            "reason": "\n".join(violations)
        }

    return {"decision": "allow", "violations": [], "reason": ""}


SNAPSHOT_FILENAME = os.path.normpath(os.path.join(".agents", ".baseline_hashes.json"))


def save_baseline_snapshot(root_dir: str, target_paths: list[str]) -> dict[str, str]:
    """세션 시작 시점의 불변 대상 파일 해시를 캡처하여 안전하게 저장."""
    import json
    baseline: dict[str, str] = {}
    for target in target_paths:
        baseline.update(capture_directory_hashes(target, root_dir))

    snap_abs = os.path.join(root_dir, SNAPSHOT_FILENAME)
    try:
        os.makedirs(os.path.dirname(snap_abs), exist_ok=True)
        with open(snap_abs, "w", encoding="utf-8") as f:
            json.dump(baseline, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return baseline


def load_baseline_snapshot(root_dir: str) -> dict[str, str]:
    """저장된 베이스라인 스냅샷 로드 (부재 시 빈 딕셔너리 반환)."""
    import json
    snap_abs = os.path.join(root_dir, SNAPSHOT_FILENAME)
    if not os.path.exists(snap_abs):
        return {}
    try:
        with open(snap_abs, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def clear_baseline_snapshot(root_dir: str) -> None:
    """작업 완료 후 베이스라인 스냅샷 자동 정리 (Clean Restore)."""
    snap_abs = os.path.join(root_dir, SNAPSHOT_FILENAME)
    if os.path.exists(snap_abs):
        try:
            os.remove(snap_abs)
        except Exception:
            pass


def run_hash_integrity_gate(project_root: str, cfg: dict) -> tuple[bool, str]:
    """Stop 훅 전용 해시 무결성 검증을 일괄 수행하고 (통과여부, 에러메시지)를 반환하는 조율 함수."""
    switches = cfg.get("switches", {})
    if not switches.get("verify_hash_immutability", True):
        return True, ""

    hash_policy = cfg.get("hash_guard_policy", DEFAULT_HASH_POLICY)
    work_mode = os.environ.get("GIT_WORK_MODE", cfg.get("current_work_mode", "default")).strip().lower()

    baseline = load_baseline_snapshot(project_root)
    if not baseline:
        return True, ""

    extra_test_dirs = []
    try:
        from core.stop_gate.multistack_scanner_core import collect_all_test_dirs
        extra_test_dirs = collect_all_test_dirs(project_root)
    except Exception:
        pass

    current_hashes: dict[str, str] = {}
    check_targets = (
        hash_policy.get("sanctuary_paths", [])
        + hash_policy.get("refactor_immutable_dirs", [])
        + hash_policy.get("fix_immutable_dirs", [])
        + extra_test_dirs
    )
    for target in set(check_targets):
        current_hashes.update(capture_directory_hashes(target, project_root))

    active_policy = dict(hash_policy)
    if extra_test_dirs:
        active_policy["refactor_immutable_dirs"] = list(set(hash_policy.get("refactor_immutable_dirs", []) + extra_test_dirs))

    hash_res = verify_hash_integrity(
        baseline=baseline,
        current=current_hashes,
        work_mode=work_mode,
        policy=active_policy
    )
    if hash_res.get("decision") == "block":
        # 스마트 싱크 (Smart Sync): 사장님 승인 하에 이미 Git 커밋 완료(Clean) 상태라면 합법적 변경으로 인정
        import subprocess
        try:
            st = subprocess.run(["git", "status", "--porcelain"], cwd=project_root, capture_output=True, text=True, timeout=3)
            if st.returncode == 0 and not st.stdout.strip():
                clear_baseline_snapshot(project_root)
                return True, ""
        except Exception:
            pass

        reason_msg = hash_res.get("reason", "해시 무결성 위반")
        error_output = (
            f"[Hash Guard 차단: 3대 급소 불변성 위반 감지]\n{reason_msg}\n"
            "철칙: 성역화 파일/테스트/데이터 무단 변조를 즉시 롤백하세요.\n"
            "[직언 가이드]: 비즈니스 코드가 정상인데 훅의 오탐/버그로 판단될 경우, 임의 우회하지 말고 즉시 사장님께 [훅 오탐 분석 및 수리 직언 보고]를 올리세요."
        )
        return False, error_output

    clear_baseline_snapshot(project_root)
    return True, ""


