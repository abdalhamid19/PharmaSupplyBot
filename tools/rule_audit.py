"""Local rule audit for file length, function length, line length, and docstrings."""

from __future__ import annotations

import ast
from pathlib import Path


MAX_FILE_LINES = 100
MAX_FUNCTION_LINES = 20
MAX_LINE_LENGTH = 100
ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "run.py",
    ROOT / "streamlit_app.py",
    *sorted((ROOT / "src").rglob("*.py")),
]
EXCEPTED_FILE_LENGTHS = {
    "src/core/drug_matching/indexer.py",
    "src/core/drug_matching/normalizer.py",
    "src/core/matching_rules.py",
    "src/core/product_matching.py",
    "src/tawreed/tawreed.py",
    "src/tawreed/tawreed_checkout.py",
    "src/tawreed/tawreed_match_logs.py",
    "src/tawreed/tawreed_products_flow.py",
    "src/tawreed/tawreed_session.py",
}
BASELINE_VIOLATIONS = {
    "src/cli/cli_match_products.py:81:function_lines:_api_config:23",
    "src/cli/cli_match_products.py:file_lines:128",
    "src/cli/cli_parser_match_products.py:10:function_lines:build_match_products_parser:36",
    "src/core/drug_matching/ai_health.py:117:function_lines:extract_quota_headers:86",
    "src/core/drug_matching/ai_health.py:243:function_lines:empty_result:39",
    "src/core/drug_matching/ai_health.py:284:function_lines:test_one:30",
    "src/core/drug_matching/ai_health.py:316:function_lines:_handle_response:23",
    "src/core/drug_matching/ai_health.py:371:function_lines:run_health_checks:27",
    "src/core/drug_matching/ai_health.py:85:function_lines:reset_in_text:22",
    "src/core/drug_matching/ai_health.py:AIKey:docstring",
    "src/core/drug_matching/ai_health.py:build_payload:docstring",
    "src/core/drug_matching/ai_health.py:content_from_response:docstring",
    "src/core/drug_matching/ai_health.py:dedupe:docstring",
    "src/core/drug_matching/ai_health.py:empty_result:docstring",
    "src/core/drug_matching/ai_health.py:file_lines:428",
    "src/core/drug_matching/ai_health.py:healthy_combos:docstring",
    "src/core/drug_matching/ai_health.py:mask_key:docstring",
    "src/core/drug_matching/ai_health.py:run_health_checks:docstring",
    "src/core/drug_matching/ai_health.py:split_csv:docstring",
    "src/core/drug_matching/ai_health.py:test_one:docstring",
    "src/core/drug_matching/ai_health.py:validate_model_json:docstring",
    "src/core/drug_matching/ai_health.py:write_reports:docstring",
    "src/core/drug_matching/ai_rotation.py:271:function_lines:_provider_attempts:23",
    "src/core/drug_matching/ai_rotation.py:AIModelAttempt:docstring",
    "src/core/drug_matching/ai_rotation.py:configured_attempts:docstring",
    "src/core/drug_matching/ai_rotation.py:file_lines:346",
    "src/core/drug_matching/ai_rotation.py:rank_attempts:docstring",
    "src/core/drug_matching/ai_rotation_health.py:173:function_lines:attempts_from_health:23",
    "src/core/drug_matching/ai_rotation_health.py:22:function_lines:run_rotation_health:30",
    "src/core/drug_matching/ai_rotation_health.py:269:function_lines:health_status:27",
    "src/core/drug_matching/ai_rotation_health.py:54:function_lines:select_preflight_attempts:21",
    "src/core/drug_matching/ai_rotation_health.py:77:function_lines:attempts_from_partial_health:27",
    "src/core/drug_matching/ai_rotation_health.py:attempts_from_health:docstring",
    "src/core/drug_matching/ai_rotation_health.py:attempts_from_partial_health:docstring",
    "src/core/drug_matching/ai_rotation_health.py:cached_working_attempts:docstring",
    "src/core/drug_matching/ai_rotation_health.py:fallback_tier:docstring",
    "src/core/drug_matching/ai_rotation_health.py:file_lines:347",
    "src/core/drug_matching/ai_rotation_health.py:health_status:docstring",
    "src/core/drug_matching/ai_rotation_health.py:load_latest_rotation_health:docstring",
    "src/core/drug_matching/ai_rotation_health.py:rank_health_rows:docstring",
    "src/core/drug_matching/ai_rotation_health.py:rotation_recommendation:docstring",
    "src/core/drug_matching/ai_rotation_health.py:run_rotation_health:docstring",
    "src/core/drug_matching/ai_rotation_health.py:select_preflight_attempts:docstring",
    "src/core/drug_matching/ai_rotation_health.py:write_rotation_reports:docstring",
    "src/core/drug_matching/ai_steps.py:118:function_lines:run_ai_review:59",
    "src/core/drug_matching/ai_steps.py:182:function_lines:run_ai_search:46",
    "src/core/drug_matching/ai_steps.py:232:function_lines:_select_for_verification:21",
    "src/core/drug_matching/ai_steps.py:283:function_lines:_apply_verification:41",
    "src/core/drug_matching/ai_steps.py:326:function_lines:_handle_rejected:59",
    "src/core/drug_matching/ai_steps.py:417:function_lines:_search_batch:25",
    "src/core/drug_matching/ai_steps.py:444:function_lines:_try_search_one:93",
    "src/core/drug_matching/ai_steps.py:64:function_lines:run_ai_verification:52",
    "src/core/drug_matching/ai_steps.py:795:function_lines:_select_for_review:26",
    "src/core/drug_matching/ai_steps.py:823:function_lines:_build_review_items:21",
    "src/core/drug_matching/ai_steps.py:824:line_length:116",
    "src/core/drug_matching/ai_steps.py:837:line_length:111",
    "src/core/drug_matching/ai_steps.py:862:function_lines:_apply_review_results:162",
    "src/core/drug_matching/ai_steps.py:file_lines:1037",
    "src/core/drug_matching/config.py:file_lines:222",
    "src/core/drug_matching/pipeline.py:100:function_lines:_match_one:57",
    "src/core/drug_matching/pipeline.py:178:function_lines:_make_row:33",
    "src/core/drug_matching/pipeline.py:337:function_lines:print_stats:35",
    "src/core/drug_matching/pipeline.py:51:function_lines:load_data:29",
    "src/core/drug_matching/pipeline.py:file_lines:421",
    "src/core/drug_matching/prompts.py:16:line_length:176",
    "src/core/drug_matching/prompts.py:26:line_length:163",
    "src/core/drug_matching/prompts.py:38:line_length:172",
    "src/core/drug_matching/prompts.py:47:line_length:176",
    "src/core/drug_matching/prompts.py:render_prompt:docstring",
    "src/core/drug_matching/trace_log.py:1008:line_length:111",
    "src/core/drug_matching/trace_log.py:116:function_lines:log_candidate_generated:24",
    "src/core/drug_matching/trace_log.py:141:function_lines:log_score_breakdown:33",
    "src/core/drug_matching/trace_log.py:175:function_lines:log_brand_lookup:40",
    "src/core/drug_matching/trace_log.py:216:function_lines:log_fuzzy_step:40",
    "src/core/drug_matching/trace_log.py:257:function_lines:log_component_check:31",
    "src/core/drug_matching/trace_log.py:289:function_lines:log_final:28",
    "src/core/drug_matching/trace_log.py:320:function_lines:log_ai_verify_sent:31",
    "src/core/drug_matching/trace_log.py:352:function_lines:log_ai_verify_result:38",
    "src/core/drug_matching/trace_log.py:391:function_lines:log_ai_search_sent:24",
    "src/core/drug_matching/trace_log.py:416:function_lines:log_ai_search_result:48",
    "src/core/drug_matching/trace_log.py:465:function_lines:log_ai_review_sent:35",
    "src/core/drug_matching/trace_log.py:482:line_length:110",
    "src/core/drug_matching/trace_log.py:494:line_length:115",
    "src/core/drug_matching/trace_log.py:501:function_lines:log_ai_review_result:33",
    "src/core/drug_matching/trace_log.py:521:line_length:112",
    "src/core/drug_matching/trace_log.py:527:line_length:113",
    "src/core/drug_matching/trace_log.py:53:function_lines:_base:27",
    "src/core/drug_matching/trace_log.py:620:function_lines:log_rotation_ranked_attempt:22",
    "src/core/drug_matching/trace_log.py:643:function_lines:log_api_attempts:26",
    "src/core/drug_matching/trace_log.py:670:function_lines:_append_rotation_attempt_event:30",
    "src/core/drug_matching/trace_log.py:760:function_lines:_summary_row:40",
    "src/core/drug_matching/trace_log.py:859:function_lines:_save_txt:23",
    "src/core/drug_matching/trace_log.py:883:function_lines:_write_step:164",
    "src/core/drug_matching/trace_log.py:997:line_length:111",
    "src/core/drug_matching/trace_log.py:file_lines:1046",
    "src/core/drug_matching/verifier.py:158:function_lines:_format_candidate:22",
    "src/core/drug_matching/verifier.py:166:line_length:135",
    "src/core/drug_matching/verifier.py:238:line_length:104",
    "src/core/drug_matching/verifier.py:420:function_lines:_call_api:202",
    "src/core/drug_matching/verifier.py:531:line_length:102",
    "src/core/drug_matching/verifier.py:58:function_lines:_extract_json:44",
    "src/core/drug_matching/verifier.py:623:function_lines:verify_one:40",
    "src/core/drug_matching/verifier.py:659:line_length:106",
    "src/core/drug_matching/verifier.py:664:function_lines:verify_batch:24",
    "src/core/drug_matching/verifier.py:689:function_lines:review_one:91",
    "src/core/drug_matching/verifier.py:745:line_length:106",
    "src/core/drug_matching/verifier.py:781:function_lines:review_batch:28",
    "src/core/drug_matching/verifier.py:810:function_lines:find_better_match:73",
    "src/core/drug_matching/verifier.py:file_lines:882",
    "src/core/drug_matching/indexer.py:145:function_lines:_component_lookup:23",
    "src/core/drug_matching/indexer.py:261:function_lines:best_match:21",
    "src/core/drug_matching/indexer.py:26:function_lines:__init__:22",
    "src/core/drug_matching/indexer.py:283:function_lines:best_match_detailed:96",
    "src/core/drug_matching/indexer.py:92:function_lines:_brand_lookup:26",
    "src/core/drug_matching/normalizer.py:174:function_lines:normalize:36",
    "src/core/drug_matching/normalizer.py:211:function_lines:parse_drug:105",
    "src/core/drug_matching/normalizer.py:318:function_lines:_canonical_form:22",
    "src/core/drug_matching/normalizer.py:342:function_lines:_infer_missing_dosage:35",
    "src/core/drug_matching/normalizer.py:410:function_lines:brand_variants_from_words:31",
    "src/core/drug_matching/normalizer.py:454:function_lines:_modifier_is_optional:26",
    "src/core/drug_matching/normalizer.py:627:function_lines:components_match:111",
    "src/cli/cli_order.py:file_lines:132",
    "src/cli/cli_parser_order.py:22:function_lines:_add_order_runtime_arguments:23",
    "src/core/cart_removal_items.py:file_lines:115",
    "src/core/matching_rules.py:file_lines:150",
    "src/core/prevented_items.py:94:function_lines:filter_prevented_order_items:25",
    "src/core/prevented_items.py:file_lines:196",
    "src/core/product_matching.py:file_lines:481",
    "src/core/utils/excel.py:file_lines:144",
    "src/tawreed/selectors.py:file_lines:122",
    "src/tawreed/tawreed.py:152:function_lines:place_order_from_items:27",
    "src/tawreed/tawreed.py:180:function_lines:remove_cart_items:25",
    "src/tawreed/tawreed.py:273:function_lines:_process_single_item:53",
    "src/tawreed/tawreed.py:302:line_length:105",
    "src/tawreed/tawreed.py:312:line_length:104",
    "src/tawreed/tawreed.py:421:function_lines:_record_item_summary:27",
    "src/tawreed/tawreed.py:61:function_lines:__init__:25",
    "src/tawreed/tawreed.py:95:function_lines:_auth:52",
    "src/tawreed/tawreed.py:file_lines:484",
    "src/tawreed/tawreed_artifacts.py:64:line_length:101",
    "src/tawreed/tawreed_artifacts.py:file_lines:187",
    "src/tawreed/tawreed_auth_waits.py:14:function_lines:wait_for_login_detection:30",
    "src/tawreed/tawreed_auth_waits.py:file_lines:102",
    "src/tawreed/tawreed_cart_removal.py:33:function_lines:remove_items_from_cart:35",
    "src/tawreed/tawreed_cart_removal.py:67:line_length:101",
    "src/tawreed/tawreed_cart_removal.py:83:line_length:112",
    "src/tawreed/tawreed_cart_removal.py:file_lines:206",
    "src/tawreed/tawreed_checkout.py:11:function_lines:confirm_order:22",
    "src/tawreed/tawreed_checkout.py:file_lines:115",
    "src/tawreed/tawreed_match_logs.py:67:function_lines:append_order_result_summary:24",
    "src/tawreed/tawreed_match_logs.py:file_lines:313",
    "src/tawreed/tawreed_products_flow.py:1001:function_lines:_decisive_match:28",
    "src/tawreed/tawreed_products_flow.py:254:function_lines:add_item_from_store_dialogs:34",
    "src/tawreed/tawreed_products_flow.py:290:function_lines:choose_next_store_for_remaining_quantity:32",
    "src/tawreed/tawreed_products_flow.py:524:function_lines:close_visible_dialogs:21",
    "src/tawreed/tawreed_products_flow.py:660:function_lines:_first_discount_value:21",
    "src/tawreed/tawreed_products_flow.py:file_lines:1049",
    "src/tawreed/tawreed_session.py:181:function_lines:ensure_logged_in:21",
    "src/tawreed/tawreed_session.py:23:line_length:104",
    "src/tawreed/tawreed_session.py:82:function_lines:wait_for_login_detection:22",
    "src/tawreed/tawreed_session.py:file_lines:259",
    "src/tawreed/tawreed_strategy.py:99:line_length:102",
    "src/tawreed/tawreed_strategy.py:file_lines:115",
    "src/ui/streamlit_headless_auth.py:33:line_length:106",
    "src/ui/streamlit_main.py:15:line_length:133",
    "src/ui/streamlit_order.py:105:function_lines:start_order_process:21",
    "src/ui/streamlit_order.py:179:function_lines:order_command:25",
    "src/ui/streamlit_order.py:22:function_lines:render_order_tab:25",
    "src/ui/streamlit_order.py:67:function_lines:render_running_order_controls:36",
    "src/ui/streamlit_order.py:file_lines:203",
    "src/ui/streamlit_order_form.py:102:function_lines:render_prevented_items_editor:40",
    "src/ui/streamlit_order_form.py:198:function_lines:profile_run_fields:24",
    "src/ui/streamlit_order_form.py:53:function_lines:render_prevented_items_manager:28",
    "src/ui/streamlit_order_form.py:83:line_length:103",
    "src/ui/streamlit_order_form.py:file_lines:235",
    "src/ui/streamlit_overview.py:69:function_lines:render_input_files_table:24",
    "src/ui/streamlit_overview.py:file_lines:112",
    "src/ui/streamlit_process.py:16:line_length:111",
    "src/ui/streamlit_process.py:26:function_lines:start_cli_subprocess:22",
    "src/ui/streamlit_process.py:file_lines:134",
    "src/ui/streamlit_remove_cart.py:132:function_lines:render_running_remove_cart_controls:29",
    "src/ui/streamlit_remove_cart.py:35:function_lines:remove_cart_form_values:26",
    "src/ui/streamlit_remove_cart.py:file_lines:191",
    "src/ui/streamlit_results.py:file_lines:139",
}


def main() -> int:
    """Run the repository rule audit and fail only on newly introduced violations."""
    violations = collect_violations()
    unexpected = unexpected_violations(violations)
    if not unexpected:
        print("rule_audit_ok")
        remaining = baseline_violations(violations)
        if remaining:
            print(f"baseline_violations_remaining:{len(remaining)}")
        return 0
    print("rule_audit_violations")
    for violation in unexpected:
        print(violation)
    return 1


def collect_violations() -> list[str]:
    """Return every current audit violation across repository targets."""
    violations: list[str] = []
    for path in TARGETS:
        violations.extend(file_length_violations(path))
        violations.extend(line_length_violations(path))
        violations.extend(function_length_violations(path))
        violations.extend(docstring_violations(path))
    return violations


def unexpected_violations(violations: list[str]) -> list[str]:
    """Return violations that are not part of the accepted baseline debt."""
    return sorted(
        violation
        for violation in violations
        if violation_key(violation) not in BASELINE_VIOLATION_KEYS
    )


def baseline_violations(violations: list[str]) -> list[str]:
    """Return the known baseline violations that still remain in the codebase."""
    return sorted(
        violation
        for violation in violations
        if violation_key(violation) in BASELINE_VIOLATION_KEYS
    )


def file_length_violations(path: Path) -> list[str]:
    """Return file-length violations for one target file."""
    relative = relative_path(path)
    line_count = len(path.read_text(encoding="utf-8").splitlines())
    if line_count <= MAX_FILE_LINES:
        return []
    if relative in EXCEPTED_FILE_LENGTHS:
        return []
    return [f"{relative}:file_lines:{line_count}"]


def line_length_violations(path: Path) -> list[str]:
    """Return line-length violations for one target file."""
    violations: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if len(line) > MAX_LINE_LENGTH:
            violations.append(f"{relative_path(path)}:{line_number}:line_length:{len(line)}")
    return violations


def function_length_violations(path: Path) -> list[str]:
    """Return function-length violations for one target file."""
    violations: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        function_length = getattr(node, "end_lineno", node.lineno) - node.lineno + 1
        if function_length > MAX_FUNCTION_LINES:
            violations.append(
                f"{relative_path(path)}:{node.lineno}:function_lines:{node.name}:{function_length}"
            )
    return violations


def docstring_violations(path: Path) -> list[str]:
    """Return missing public docstring violations for one target file."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    violations: list[str] = []
    if ast.get_docstring(tree) is None:
        violations.append(f"{relative_path(path)}:module_docstring")
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if node.name.startswith("_"):
            continue
        if ast.get_docstring(node) is None:
            violations.append(f"{relative_path(path)}:{node.name}:docstring")
    return violations


def relative_path(path: Path) -> str:
    """Return the repository-relative path for one target file."""
    return path.relative_to(ROOT).as_posix()


def violation_key(violation: str) -> str:
    """Return a stable identity for one violation even when measured values improve."""
    parts = violation.split(":")
    if len(parts) == 3 and parts[1] == "file_lines":
        return f"{parts[0]}:file_lines"
    if len(parts) == 4 and parts[2] == "line_length":
        return f"{parts[0]}:line_length:{parts[3]}"
    if len(parts) == 5 and parts[2] == "function_lines":
        return f"{parts[0]}:function_lines:{parts[3]}"
    return violation


BASELINE_VIOLATION_KEYS = {violation_key(violation) for violation in BASELINE_VIOLATIONS}


if __name__ == "__main__":
    raise SystemExit(main())
