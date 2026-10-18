# -*- coding: utf-8 -*-
# [파일명]: feature_boundary_core.py | [용도] 3대 계층(Features/Engine/Shared) 격리 및 피처 경계선 감찰 순수 코어 (Functional Core)
import ast
import os
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_FEATURE_BOUNDARY_POLICY: Dict[str, Any] = {
    "engine_dir": "src/engine",
    "features_dir": "src/features",
    "shared_dir": "src/shared",
    "isolation_rules": {
        "engine_cannot_import": ["features", "shared"],
        "shared_cannot_import": ["features", "engine"],
        "cross_feature_banned": True,
    },
    "bypass_features": [],
}


def _is_subpath(norm_path: str, dir_path: str) -> bool:
    """경로가 특정 디렉터리 하위인지 판별하는 순수 함수."""
    clean_dir = dir_path.strip("/\\").replace("\\", "/") + "/"
    return norm_path.startswith(clean_dir)


def _extract_feature_name(norm_path: str, features_dir: str) -> Optional[str]:
    """경로가 features_dir 하위인 경우 해당 피처 폴더명을 추출하는 순수 함수."""
    fdir = features_dir.strip("/\\").replace("\\", "/") + "/"
    if not norm_path.startswith(fdir):
        return None
    sub_path = norm_path[len(fdir):]
    parts = sub_path.split("/")
    return parts[0] if parts and parts[0] else None


def _identify_file_layer(
    norm_path: str,
    engine_dir: str,
    features_dir: str,
    shared_dir: str
) -> Tuple[str, Optional[str]]:
    """수정 대상 파일이 3대 계층 중 어디에 속하는지 식별하는 순수 함수."""
    if _is_subpath(norm_path, engine_dir):
        return "engine", None
    if _is_subpath(norm_path, shared_dir):
        return "shared", None
    if _is_subpath(norm_path, features_dir):
        feat_name = _extract_feature_name(norm_path, features_dir)
        return "features", feat_name
    return "other", None


def _identify_target_layer(
    mod: str,
    engine_dir: str,
    features_dir: str,
    shared_dir: str
) -> Tuple[Optional[str], Optional[str]]:
    """import 대상 모듈 문자열이 어느 계층을 가리키는지 식별하는 순수 함수."""
    prefixes = [
        ("engine", engine_dir.replace("/", ".").strip(".") + "."),
        ("engine", engine_dir.split("/")[-1] + "."),
        ("shared", shared_dir.replace("/", ".").strip(".") + "."),
        ("shared", shared_dir.split("/")[-1] + "."),
        ("features", features_dir.replace("/", ".").strip(".") + "."),
        ("features", features_dir.split("/")[-1] + "."),
    ]
    for layer, pfx in prefixes:
        if mod.startswith(pfx) or mod == pfx.rstrip("."):
            if layer == "features":
                rem = mod[len(pfx):] if mod.startswith(pfx) else ""
                feat_name = rem.split(".")[0] if rem else None
                return layer, feat_name
            return layer, None
    return None, None


def _format_boundary_violation(
    file_path: str,
    cur_feature: str,
    target_feature: str,
    imported_module: str,
    shared_dir: str
) -> str:
    """피처 간 횡적 참조 위반 처방전 생성 순수 함수."""
    return (
        f"[PreTool 차단: 피처 간 횡적 참조(Cross-Feature Import) 금지]\n"
        f"수정 시도 파일: '{file_path}' (피처: '{cur_feature}')\n"
        f"위반 대상 참조: '{imported_module}' (피처: '{target_feature}')\n"
        f"원인: 피처 폴더 간 직접 import는 아키텍처 헌법 위반입니다.\n"
        f"[즉시 조치 요령 (Deadlock-Free Guidance)]:\n"
        f"1. 우회 시도(__import__, 상대경로 등)는 원천 차단됩니다.\n"
        f"2. 참조하려는 함수/클래스/타입을 '{shared_dir}/' 폴더로 이동(승격)시키세요.\n"
        f"3. 양쪽 피처에서 'from {shared_dir.replace('/', '.')}...'로 하향 참조하도록 수정하세요."
    )


def _format_layer_violation(
    file_path: str,
    from_layer: str,
    to_layer: str,
    imported_module: str,
    engine_dir: str,
    features_dir: str,
    shared_dir: str
) -> str:
    """엔진 및 셰어드 격리 위반 처방전 생성 순수 함수."""
    if from_layer == "engine":
        return (
            f"[PreTool 차단: 척추 엔진(Engine) 격리 헌법 위반]\n"
            f"수정 시도 파일: '{file_path}' (계층: Engine)\n"
            f"위반 대상 참조: '{imported_module}' (계층: {to_layer})\n"
            f"원인: 시스템 척추 엔진은 외부 피처나 유틸리티를 참조할 수 없으며 100% 자급자족해야 합니다.\n"
            f"[즉시 조치 요령 (Deadlock-Free Guidance)]:\n"
            f"1. 외부 '{imported_module}' import를 즉시 제거하세요.\n"
            f"2. 필요한 연산이나 도구는 '{engine_dir}/' 내부 모듈 또는 표준 라이브러리로 자체 완결하세요."
        )
    return (
        f"[PreTool 차단: 순수 유틸(Shared) 도메인 오염 방지 헌법 위반]\n"
        f"수정 시도 파일: '{file_path}' (계층: Shared)\n"
        f"위반 대상 참조: '{imported_module}' (계층: {to_layer})\n"
        f"원인: 공통 유틸리티는 도메인 피처나 엔진에 종속될 수 없으며 순수해야 합니다.\n"
        f"[즉시 조치 요령 (Deadlock-Free Guidance)]:\n"
        f"1. 도메인 종속적인 '{imported_module}' 참조를 즉시 제거하세요.\n"
        f"2. 도메인 의존성이 필요한 로직은 '{features_dir}/' 하위 피처로 이관하세요."
    )


def check_cross_feature_import(
    file_path: str,
    file_content: str,
    config: Dict[str, Any]
) -> Tuple[bool, str]:
    """3대 계층(Engine/Features/Shared) 격리 및 피처 간 횡적 import를 감찰하는 순수 결정론적 함수."""
    switches = config.get("switches", {})
    if not switches.get("block_cross_feature_import", True):
        return True, ""

    if not file_path or not file_content:
        return True, ""

    policy = config.get("feature_boundary_policy", DEFAULT_FEATURE_BOUNDARY_POLICY)
    engine_dir = policy.get("engine_dir", "src/engine")
    features_dir = policy.get("features_dir", "src/features")
    shared_dir = policy.get("shared_dir", "src/shared")
    isolation_rules = policy.get("isolation_rules")
    bypass_features = set(policy.get("bypass_features", []))

    norm_path = file_path.replace("\\", "/").lstrip("/")
    from_layer, cur_feat = _identify_file_layer(norm_path, engine_dir, features_dir, shared_dir)

    # 3대 계층 외부 파일(main.py, tests 등)은 자유롭게 허용
    if from_layer == "other":
        return True, ""

    if from_layer == "features" and cur_feat in bypass_features:
        return True, ""

    try:
        tree = ast.parse(file_content, filename=norm_path)
    except SyntaxError:
        return True, ""

    # isolation_rules가 명시된 경우 3대 계층 매트릭스 검사
    engine_banned = set(isolation_rules.get("engine_cannot_import", ["features", "shared"])) if isolation_rules else set()
    shared_banned = set(isolation_rules.get("shared_cannot_import", ["features", "engine"])) if isolation_rules else set()
    cross_feat_banned = isolation_rules.get("cross_feature_banned", True) if isolation_rules else True

    for node in ast.walk(tree):
        modules_to_check: List[str] = []
        if isinstance(node, ast.Import):
            modules_to_check = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules_to_check = [node.module]
            elif node.level and node.level > 0:
                # 상대 경로(from ..something import ...) 감지
                modules_to_check = [f"relative_level_{node.level}"]

        for mod in modules_to_check:
            to_layer, target_feat = _identify_target_layer(mod, engine_dir, features_dir, shared_dir)

            # 1. Engine 계층 위반 감찰
            if from_layer == "engine" and to_layer in engine_banned:
                reason = _format_layer_violation(
                    file_path=norm_path,
                    from_layer=from_layer,
                    to_layer=to_layer,
                    imported_module=mod,
                    engine_dir=engine_dir,
                    features_dir=features_dir,
                    shared_dir=shared_dir,
                )
                return False, reason

            # 2. Shared 계층 위반 감찰
            if from_layer == "shared" and to_layer in shared_banned:
                reason = _format_layer_violation(
                    file_path=norm_path,
                    from_layer=from_layer,
                    to_layer=to_layer,
                    imported_module=mod,
                    engine_dir=engine_dir,
                    features_dir=features_dir,
                    shared_dir=shared_dir,
                )
                return False, reason

            # 3. Features 계층 간 횡적 침범 감찰
            if from_layer == "features" and to_layer == "features" and cross_feat_banned:
                if target_feat and target_feat != cur_feat and target_feat not in bypass_features:
                    reason = _format_boundary_violation(
                        file_path=norm_path,
                        cur_feature=cur_feat or "unknown",
                        target_feature=target_feat,
                        imported_module=mod,
                        shared_dir=shared_dir,
                    )
                    return False, reason

    return True, ""

