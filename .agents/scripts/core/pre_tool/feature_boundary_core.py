# -*- coding: utf-8 -*-
# [파일명]: feature_boundary_core.py | [용도] 피처 간 횡적 import 차단 순수 코어 (Functional Core)
import ast
import os
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_FEATURE_BOUNDARY_POLICY: Dict[str, Any] = {
    "features_dir": "src/features",
    "shared_dir": "src/shared",
    "bypass_features": [],
}


def _extract_feature_name(norm_path: str, features_dir: str) -> Optional[str]:
    """경로가 features_dir 하위인 경우 해당 피처 폴더명을 추출하는 순수 함수."""
    fdir = features_dir.strip("/\\").replace("\\", "/") + "/"
    if not norm_path.startswith(fdir):
        return None
    sub_path = norm_path[len(fdir):]
    parts = sub_path.split("/")
    return parts[0] if parts and parts[0] else None


def _format_boundary_violation(
    file_path: str,
    cur_feature: str,
    target_feature: str,
    imported_module: str,
    shared_dir: str
) -> str:
    """교착 방지 100% 명확한 행동 강령이 담긴 처방전 에러 메시지 생성 순수 함수."""
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


def check_cross_feature_import(
    file_path: str,
    file_content: str,
    config: Dict[str, Any]
) -> Tuple[bool, str]:
    """파일 내용 중 타 피처 횡적 import 여부를 감찰하는 순수 결정론적 함수."""
    switches = config.get("switches", {})
    if not switches.get("block_cross_feature_import", True):
        return True, ""

    if not file_path or not file_content:
        return True, ""

    policy = config.get("feature_boundary_policy", DEFAULT_FEATURE_BOUNDARY_POLICY)
    features_dir = policy.get("features_dir", "src/features")
    shared_dir = policy.get("shared_dir", "src/shared")
    bypass_features = set(policy.get("bypass_features", []))

    norm_path = file_path.replace("\\", "/").lstrip("/")
    cur_feature = _extract_feature_name(norm_path, features_dir)
    if not cur_feature or cur_feature in bypass_features:
        return True, ""

    try:
        tree = ast.parse(file_content, filename=norm_path)
    except SyntaxError:
        return True, ""

    prefix_a = features_dir.replace("/", ".").strip(".") + "."
    prefix_b = features_dir.split("/")[-1] + "."

    for node in ast.walk(tree):
        modules_to_check: List[str] = []
        if isinstance(node, ast.Import):
            modules_to_check = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules_to_check = [node.module]

        for mod in modules_to_check:
            target_feat: Optional[str] = None
            if mod.startswith(prefix_a):
                rem = mod[len(prefix_a):]
                target_feat = rem.split(".")[0]
            elif mod.startswith(prefix_b):
                rem = mod[len(prefix_b):]
                target_feat = rem.split(".")[0]

            if target_feat and target_feat != cur_feature and target_feat not in bypass_features:
                reason = _format_boundary_violation(
                    file_path=norm_path,
                    cur_feature=cur_feature,
                    target_feature=target_feat,
                    imported_module=mod,
                    shared_dir=shared_dir
                )
                return False, reason

    return True, ""
