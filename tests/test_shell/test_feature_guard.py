# -*- coding: utf-8 -*-
# [파일명]: test_feature_guard.py (피처 격리 헌법 가드)
# [원칙] features/ 내 각 피처는 상호 직접 import 영구 금지 (수평 침범 차단)
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Feature Horizontal Isolation Guard.
import ast
import os
import pytest


def test_feature_horizontal_isolation_guard():
    """피처 수평 격리 가드: features/<A> 내에서 features/<B> 직접 import 차단"""
    features_root = "src/features"
    if not os.path.exists(features_root):
        pytest.skip("features 디렉토리 미도입 프로젝트 통과")

    feature_dirs = [
        d for d in os.listdir(features_root)
        if os.path.isdir(os.path.join(features_root, d)) and not d.startswith((".", "_"))
    ]
    if len(feature_dirs) < 2:
        return

    violations = []
    for cur_feature in feature_dirs:
        cur_feature_path = os.path.join(features_root, cur_feature)
        other_features = [f for f in feature_dirs if f != cur_feature]

        for r, _, files in os.walk(cur_feature_path):
            for f in files:
                if not f.endswith(".py"):
                    continue
                fpath = os.path.join(r, f)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    try:
                        tree = ast.parse(fp.read(), filename=f)
                    except SyntaxError:
                        continue

                    for n in ast.walk(tree):
                        if isinstance(n, (ast.Import, ast.ImportFrom)):
                            imported_modules = []
                            if isinstance(n, ast.Import):
                                imported_modules = [a.name for a in n.names]
                            elif isinstance(n, ast.ImportFrom) and n.module:
                                imported_modules = [n.module]

                            for mod in imported_modules:
                                for other in other_features:
                                    target_patterns = [
                                        f"src.features.{other}",
                                        f"features.{other}",
                                    ]
                                    if any(mod == p or mod.startswith(p + ".") for p in target_patterns):
                                        violations.append(
                                            f"[{cur_feature} -> {other} 직접 침범]: {os.path.relpath(fpath)} -> import '{mod}'"
                                        )

    assert not violations, (
        f"[아키텍처 헌법 위반: 피처 수평 참조 감지]\n"
        + "\n".join(violations) + "\n"
        + "철칙: 타 피처 직접 import 금지. 오직 shared/ 승격 모듈이나 도메인 이벤트로만 소통하세요."
    )
