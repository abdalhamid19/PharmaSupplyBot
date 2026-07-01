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
    "src/core/drug_matching/indexing/indexer.py",
    "src/core/drug_matching/normalization/normalizer.py",
    "src/core/matching_rules.py",
    "src/core/product_matching.py",
    "src/tawreed/tawreed.py",
    "src/tawreed/tawreed_checkout.py",
    "src/tawreed/tawreed_match_logs.py",
    "src/tawreed/tawreed_products_flow.py",
    "src/tawreed/tawreed_session.py",
    # P3 merged files
    "src/cli/cli_order_items.py",
    "src/cli/cli_order.py",
    "src/cli/cli_parser.py",
    "src/cli/item_worker.py",
    "src/cli/cli_match_products.py",
    "src/ui/streamlit_order.py",
    "src/ui/streamlit_remove_cart.py",
    "src/ui/streamlit_results.py",
    "src/ui/streamlit_manual_review_cli.py",
    "src/ui/streamlit_manual_review_page.py",
    "src/ui/streamlit_manual_review_page_saved.py",
    # P1.7 merged files
    "src/core/drug_matching/tracing/trace_log_ai.py",
    "src/core/drug_matching/tracing/trace_log_ai_mixins.py",
    "src/core/drug_matching/tracing/trace_log_output.py",
    "src/core/drug_matching/tracing/trace_log_phases.py",
    "src/core/drug_matching/tracing/trace_log_candidate_scoring.py",
    "src/core/drug_matching/tracing/trace_log_summary.py",
    "src/core/drug_matching/verification/verifier_request.py",
    "src/core/drug_matching/verification/verifier_response.py",
    "src/core/drug_matching/verification/verifier_helpers.py",
    "src/core/drug_matching/verification/verifier_core.py",
    "src/core/drug_matching/verification/verifier_request_build.py",
    "src/core/drug_matching/verification/verifier_request_parse.py",
    "src/core/drug_matching/verification/verifier_methods.py",
    "src/core/drug_matching/verification/verifier_review.py",
    "src/core/drug_matching/verification/verifier_request_validate.py",
    "src/core/drug_matching/verification/verifier_search.py",
    "src/core/drug_matching/verification/verifier.py",
    "src/core/drug_matching/verification/verifier_core_extract.py",
    "src/core/drug_matching/verification/verifier_core_format.py",
    "src/core/drug_matching/indexing/indexer_scoring.py",
    "src/core/drug_matching/indexing/indexer_trace.py",
    "src/core/drug_matching/pipeline/pipeline_io.py",
    "src/core/drug_matching/pipeline/pipeline_matching.py",
    "src/tawreed/api/tawreed_api_contract_base.py",
    "src/tawreed/api/tawreed_api_contract_discovery.py",
    "src/tawreed/api/tawreed_api_flow_matching.py",
    "src/tawreed/product_export_api.py",
    "src/tawreed/product_export_rows.py",
    "src/tawreed/tawreed_match_logs_csv.py",
    "src/tawreed/tawreed_match_logs_helpers.py",
    "src/tawreed/tawreed_order_delegation.py",
    "src/tawreed/tawreed_order_match.py",
    "src/tawreed/tawreed_order_placement.py",
    "src/tawreed/api/tawreed_api_flow_multistore.py",
    "src/ui/streamlit_order_command.py",
    "src/ui/streamlit_order_form.py",
    "src/ui/streamlit_order_process.py",
}
BASELINE_VIOLATIONS = {
    "src/cli/cli_order.py:186:function_lines:run_single_profile_items:24",
    "src/cli/cli_order.py:file_lines:205",
    "src/cli/cli_match_products.py:81:function_lines:_api_config:23",
    "src/cli/cli_match_products.py:file_lines:128",
    "src/cli/cli_parser_order.py:file_lines:215",
    # P1.7 merged files - function length violations
    "src/core/drug_matching/indexing/indexer_scoring.py:53:function_lines:fuzzy_match:34",
    "src/core/drug_matching/indexing/indexer_scoring.py:88:function_lines:single_scorer_match:34",
    "src/core/drug_matching/indexing/indexer_trace.py:19:function_lines:score_events:37",
    "src/core/drug_matching/pipeline/pipeline_matching.py:112:function_lines:_make_row:27",
    "src/core/drug_matching/pipeline/pipeline_matching.py:35:function_lines:load_data:32",
    "src/core/drug_matching/tracing/trace_log_ai.py:100:function_lines:log_ai_search_sent:25",
    "src/core/drug_matching/tracing/trace_log_ai.py:126:function_lines:log_ai_search_result:49",
    "src/core/drug_matching/tracing/trace_log_ai.py:19:function_lines:log_ai_verify_sent:32",
    "src/core/drug_matching/tracing/trace_log_ai.py:202:function_lines:log_ai_review_sent:43",
    "src/core/drug_matching/tracing/trace_log_ai.py:246:function_lines:log_ai_review_result:41",
    "src/core/drug_matching/tracing/trace_log_ai.py:52:function_lines:log_ai_verify_result:39",
    "src/core/drug_matching/tracing/trace_log_ai_mixins.py:126:function_lines:_append_rotation_attempt_event:31",
    "src/core/drug_matching/tracing/trace_log_ai_mixins.py:70:function_lines:log_rotation_ranked_attempt:23",
    "src/core/drug_matching/tracing/trace_log_ai_mixins.py:98:function_lines:log_api_attempts:27",
    "src/core/drug_matching/tracing/trace_log_candidate_scoring.py:129:function_lines:log_fuzzy_step:41",
    "src/core/drug_matching/tracing/trace_log_candidate_scoring.py:13:function_lines:log_candidate_generated:29",
    "src/core/drug_matching/tracing/trace_log_candidate_scoring.py:171:function_lines:log_component_check:34",
    "src/core/drug_matching/tracing/trace_log_candidate_scoring.py:43:function_lines:log_brand_lookup:41",
    "src/core/drug_matching/tracing/trace_log_candidate_scoring.py:93:function_lines:log_score_breakdown:35",
    "src/core/drug_matching/tracing/trace_log_output.py:201:function_lines:save_txt:25",
    "src/core/drug_matching/tracing/trace_log_output.py:227:function_lines:_write_step:43",
    "src/core/drug_matching/tracing/trace_log_phases.py:78:function_lines:log_final:30",
    "src/core/drug_matching/tracing/trace_log_summary.py:129:function_lines:_ai_summary_status:21",
    "src/core/drug_matching/tracing/trace_log_summary.py:41:function_lines:_summary_row:35",
    "src/core/drug_matching/verification/verifier_core.py:60:function_lines:resolve_ai_conflicts:12",
    "src/core/drug_matching/verification/verifier_core.py:74:function_lines:hard_conflict_names:6",
    "src/core/drug_matching/verification/verifier_core.py:82:function_lines:apply_critical_conflicts:12",
    "src/core/drug_matching/verification/verifier_core.py:96:function_lines:apply_conflict_penalty:5",
    "src/core/drug_matching/verification/verifier_core.py:103:function_lines:apply_reject_decision_override:10",
    "src/core/drug_matching/verification/verifier_core.py:119:function_lines:coerce_best_index:13",
    "src/core/drug_matching/verification/verifier_core.py:134:function_lines:fallback_from_unparseable_response:10",
    "src/core/drug_matching/verification/verifier_core.py:146:function_lines:normalize_verify_item:20",
    "src/core/drug_matching/verification/verifier_core.py:168:function_lines:normalize_review_item:5",
    "src/core/drug_matching/verification/verifier_helpers.py:39:function_lines:extract_json:47",
    "src/core/drug_matching/verification/verifier_helpers.py:225:function_lines:format_candidate:27",
    "src/core/drug_matching/verification/verifier_request.py:32:function_lines:call_api:27",
    "src/core/drug_matching/verification/verifier_request.py:59:function_lines:_ensure_session:13",
    "src/core/drug_matching/verification/verifier_request.py:73:function_lines:_execute_request_plan:9",
    "src/core/drug_matching/verification/verifier_request.py:83:function_lines:_try_plan_item:30",
    "src/core/drug_matching/verification/verifier_request.py:114:function_lines:_make_single_request:31",
    "src/core/drug_matching/verification/verifier_request.py:146:function_lines:_build_fallback_response:7",
    "src/core/drug_matching/verification/verifier_request_build.py:20:function_lines:rotation_request_plan:18",
    "src/core/drug_matching/verification/verifier_request_build.py:39:function_lines:rotation_attempts_for:14",
    "src/core/drug_matching/verification/verifier_request_build.py:54:function_lines:strong_enough_review_attempts:9",
    "src/core/drug_matching/verification/verifier_request_build.py:64:function_lines:primary_rotation_attempt:6",
    "src/core/drug_matching/verification/verifier_request_build.py:70:function_lines:attempt_strength:2",
    "src/core/drug_matching/verification/verifier_request_build.py:74:function_lines:rotated_tier_plan:15",
    "src/core/drug_matching/verification/verifier_request_build.py:90:function_lines:rotation_plan_item:13",
    "src/core/drug_matching/verification/verifier_request_build.py:104:function_lines:rotation_cursor_key:8",
    "src/core/drug_matching/verification/verifier_request_build.py:113:function_lines:record_rotation_used:7",
    "src/core/drug_matching/verification/verifier_request_build.py:142:function_lines:build_attempt_plan:18",
    "src/core/drug_matching/verification/verifier_request_build.py:161:function_lines:build_request_plan:7",
    "src/core/drug_matching/verification/verifier_request_build.py:169:function_lines:record_rotation_used:2",
    "src/core/drug_matching/verification/verifier_request_build.py:172:function_lines:combo_key:4",
    "src/core/drug_matching/verification/verifier_request_parse.py:30:function_lines:handle_response:16",
    "src/core/drug_matching/verification/verifier_request_parse.py:47:function_lines:_handle_rate_limit:21",
    "src/core/drug_matching/verification/verifier_request_parse.py:69:function_lines:_handle_error_response:25",
    "src/core/drug_matching/verification/verifier_request_parse.py:95:function_lines:_handle_success_response:34",
    "src/core/drug_matching/verification/verifier_request_parse.py:130:function_lines:_handle_parse_failure:20",
    "src/core/drug_matching/verification/verifier_request_validate.py:22:function_lines:record_combo_failure:15",
    "src/core/drug_matching/verification/verifier_request_validate.py:38:function_lines:log_combo_failure:12",
    "src/core/drug_matching/verification/verifier_search.py:20:function_lines:find_better_match:73",
    "src/core/drug_matching/verification/verifier_response.py:25:function_lines:process_api_response:3",
    "src/core/drug_matching/verification/verifier_response.py:54:function_lines:_handle_success_response:44",
    "src/core/drug_matching/verification/verifier_response.py:103:function_lines:_handle_rate_limit:29",
    "src/core/drug_matching/verification/verifier_response.py:133:function_lines:_handle_error_response:37",
    "src/core/drug_matching/verification/verifier_response.py:175:function_lines:_handle_parse_failure:27",
    # P1.7 merged files - tawreed function length violations
    "src/tawreed/product_export_api.py:57:function_lines:iter_all_product_candidates:21",
    "src/tawreed/api/tawreed_api_flow_main.py:13:function_lines:match_items_only_with_api:21",
    "src/tawreed/api/tawreed_api_flow_matching.py:12:function_lines:require_api_match:35",
    "src/tawreed/api/tawreed_api_flow_matching.py:132:function_lines:_raise_non_orderable_exception:31",
    "src/tawreed/api/tawreed_api_flow_multistore.py:45:function_lines:_select_stores_and_add_to_cart:24",
    "src/tawreed/tawreed_order_placement.py:70:function_lines:place_order_from_items:36",
    # P1.7 merged files - ui line length violation
    "src/ui/streamlit_order_process.py:127:line_length:103",
    "src/core/config/config_factory.py:65:line_length:190",
    "src/core/config/config_factory.py:75:line_length:112",
    "src/core/config/config_factory.py:77:line_length:284",
    "src/core/config/config_updater.py:27:line_length:135",
    "src/core/drug_matching/ai/ai_health_quota.py:9:function_lines:extract_quota_headers:86",
    "src/core/drug_matching/ai/ai_health_test_constants.py:AIKey:docstring",
    "src/core/drug_matching/ai/ai_health_test_execution.py:21:function_lines:test_one:31",
    "src/core/drug_matching/ai/ai_health_test_execution.py:54:function_lines:_handle_response:25",
    "src/core/drug_matching/ai/ai_health_test_execution.py:81:function_lines:run_health_checks:28",
    "src/core/drug_matching/ai/ai_health_test_execution.py:file_lines:111",
    "src/core/drug_matching/ai/ai_health_test_payload.py:24:function_lines:empty_result:40",
    "src/core/drug_matching/ai/ai_health_utils.py:52:function_lines:reset_in_text:22",
    "src/core/drug_matching/ai/ai_review.py:34:function_lines:run_ai_review:59",
    "src/core/drug_matching/ai/ai_review_result_applier.py:34:function_lines:apply_results:60",
    "src/core/drug_matching/ai/ai_review_scenario_handlers.py:15:function_lines:handle_api_failed:40",
    "src/core/drug_matching/ai/ai_review_scenario_handlers.py:77:function_lines:handle_disagreement:69",
    "src/core/drug_matching/ai/ai_review_scenario_handlers.py:file_lines:145",
    "src/core/drug_matching/ai/ai_review_selection.py:34:function_lines:_build_review_items:21",
    "src/core/drug_matching/ai/ai_review_selection.py:35:line_length:116",
    "src/core/drug_matching/ai/ai_review_selection.py:48:line_length:111",
    "src/core/drug_matching/ai/ai_review_selection.py:6:function_lines:_select_for_review:26",
    "src/core/drug_matching/ai/ai_rotation_config.py:file_lines:210",
    "src/core/drug_matching/ai/ai_rotation_health_execution.py:12:function_lines:run_rotation_health:34",
    "src/core/drug_matching/ai/ai_rotation_health_execution.py:run_rotation_health:docstring",
    "src/core/drug_matching/ai/ai_rotation_health_reports.py:load_latest_rotation_health:docstring",
    "src/core/drug_matching/ai/ai_rotation_health_reports.py:write_rotation_reports:docstring",
    "src/core/drug_matching/ai/ai_rotation_health_scoring.py:5:line_length:114",
    "src/core/drug_matching/ai/ai_rotation_health_scoring.py:rank_health_rows:docstring",
    "src/core/drug_matching/ai/ai_rotation_health_selection.py:30:function_lines:attempts_from_partial_health:27",
    "src/core/drug_matching/ai/ai_rotation_health_selection.py:59:function_lines:cached_working_attempts:24",
    "src/core/drug_matching/ai/ai_rotation_health_selection.py:7:function_lines:select_preflight_attempts:21",
    "src/core/drug_matching/ai/ai_rotation_health_selection.py:85:function_lines:attempts_from_health:23",
    "src/core/drug_matching/ai/ai_rotation_health_selection.py:attempts_from_health:docstring",
    "src/core/drug_matching/ai/ai_rotation_health_selection.py:attempts_from_partial_health:docstring",
    "src/core/drug_matching/ai/ai_rotation_health_selection.py:cached_working_attempts:docstring",
    "src/core/drug_matching/ai/ai_rotation_health_selection.py:file_lines:148",
    "src/core/drug_matching/ai/ai_rotation_health_selection.py:select_preflight_attempts:docstring",
    "src/core/drug_matching/ai/ai_rotation_health_status.py:9:function_lines:health_status:27",
    "src/core/drug_matching/ai/ai_rotation_health_status.py:fallback_tier:docstring",
    "src/core/drug_matching/ai/ai_rotation_health_status.py:health_status:docstring",
    "src/core/drug_matching/ai/ai_rotation_health_status.py:rotation_recommendation:docstring",
    "src/core/drug_matching/ai/ai_search.py:25:function_lines:run_ai_search:46",
    "src/core/drug_matching/ai/ai_search_candidates.py:file_lines:137",
    "src/core/drug_matching/ai/ai_search_core_batch.py:14:function_lines:_search_batch:26",
    "src/core/drug_matching/ai/ai_search_core_execution.py:23:function_lines:_try_search_one:29",
    "src/core/drug_matching/ai/ai_search_core_execution.py:54:function_lines:_execute_search_and_apply:27",
    "src/core/drug_matching/ai/ai_search_core_execution.py:file_lines:108",
    "src/core/drug_matching/ai/ai_search_core_logging.py:49:function_lines:_log_search_failure:23",
    "src/core/drug_matching/ai/ai_verify_batch.py:26:function_lines:_apply_verification:42",
    "src/core/drug_matching/ai/ai_verify_handlers.py:13:function_lines:_handle_rejected:30",
    "src/core/drug_matching/ai/ai_verify_main.py:20:function_lines:run_ai_verification:27",
    "src/core/drug_matching/ai/ai_verify_rejection.py:16:function_lines:_handle_rejected:60",
    "src/core/drug_matching/ai/ai_verify_selection.py:10:function_lines:_select_for_verification:22",
    "src/core/drug_matching/indexing/indexer_build.py:29:function_lines:_process_dataframe:21",
    "src/core/drug_matching/indexing/indexer_build.py:file_lines:141",
    "src/core/drug_matching/indexing/indexer_detailed.py:106:function_lines:component_lookup:31",
    "src/core/drug_matching/indexing/indexer_detailed.py:166:function_lines:_component_score:21",
    "src/core/drug_matching/indexing/indexer_detailed.py:188:function_lines:brand_lookup:30",
    "src/core/drug_matching/indexing/indexer_detailed.py:250:function_lines:fuzzy_match:34",
    "src/core/drug_matching/indexing/indexer_detailed.py:285:function_lines:single_scorer_match:34",
    "src/core/drug_matching/indexing/indexer_detailed.py:325:function_lines:__init__:23",
    "src/core/drug_matching/indexing/indexer_detailed.py:345:line_length:107",
    "src/core/drug_matching/indexing/indexer_detailed.py:358:function_lines:best_match_detailed:94",
    "src/core/drug_matching/indexing/indexer_detailed.py:436:line_length:104",
    "src/core/drug_matching/indexing/indexer_detailed.py:file_lines:464",
    "src/core/drug_matching/indexing/indexer_lookup.py:146:function_lines:_component_score:21",
    "src/core/drug_matching/indexing/indexer_lookup.py:246:function_lines:find_best_match:24",
    "src/core/drug_matching/indexing/indexer_lookup.py:24:function_lines:lookup:27",
    "src/core/drug_matching/indexing/indexer_lookup.py:99:function_lines:lookup:28",
    "src/core/drug_matching/indexing/indexer_lookup.py:file_lines:335",
    "src/core/drug_matching/indexing/indexer_search.py:13:function_lines:__init__:28",
    "src/core/drug_matching/indexing/indexer_search.py:file_lines:104",
    "src/core/drug_matching/normalization/normalizer_constants.py:file_lines:116",
    "src/core/drug_matching/normalization/normalizer_matching_brand.py:14:line_length:106",
    "src/core/drug_matching/normalization/normalizer_matching_brand.py:15:line_length:106",
    "src/core/drug_matching/normalization/normalizer_matching_brand.py:27:line_length:127",
    "src/core/drug_matching/normalization/normalizer_matching_brand.py:41:line_length:105",
    "src/core/drug_matching/normalization/normalizer_matching_brand.py:9:function_lines:_brand_match_check:30",
    "src/core/drug_matching/normalization/normalizer_matching_brand.py:9:line_length:104",
    "src/core/drug_matching/normalization/normalizer_matching_core.py:20:function_lines:components_match:86",
    "src/core/drug_matching/normalization/normalizer_matching_core.py:20:line_length:106",
    "src/core/drug_matching/normalization/normalizer_matching_core.py:36:line_length:125",
    "src/core/drug_matching/normalization/normalizer_matching_core.py:43:line_length:109",
    "src/core/drug_matching/normalization/normalizer_matching_core.py:73:line_length:125",
    "src/core/drug_matching/normalization/normalizer_matching_core.py:92:line_length:110",
    "src/core/drug_matching/normalization/normalizer_matching_core.py:file_lines:110",
    "src/core/drug_matching/normalization/normalizer_matching_dosage_compatibility.py:114:line_length:101",
    "src/core/drug_matching/normalization/normalizer_matching_dosage_compatibility.py:118:line_length:153",
    "src/core/drug_matching/normalization/normalizer_matching_dosage_compatibility.py:file_lines:131",
    "src/core/drug_matching/normalization/normalizer_matching_dosage_core.py:14:function_lines:_dosage_match_check:30",
    "src/core/drug_matching/normalization/normalizer_matching_dosage_core.py:41:line_length:116",
    "src/core/drug_matching/normalization/normalizer_matching_form.py:9:function_lines:_other_match_check:34",
    "src/core/drug_matching/normalization/normalizer_matching_helpers.py:26:line_length:117",
    "src/core/drug_matching/normalization/normalizer_matching_helpers.py:28:line_length:109",
    "src/core/drug_matching/normalization/normalizer_matching_helpers.py:30:line_length:173",
    "src/core/drug_matching/normalization/normalizer_matching_helpers.py:36:line_length:127",
    "src/core/drug_matching/normalization/normalizer_matching_numeric.py:32:line_length:101",
    "src/core/drug_matching/normalization/normalizer_parsing_classification.py:30:function_lines:brand_variants_from_words:24",
    "src/core/drug_matching/normalization/normalizer_parsing_classification.py:brand_variants_from_words:docstring",
    "src/core/drug_matching/normalization/normalizer_parsing_classification.py:classify_product:docstring",
    "src/core/drug_matching/normalization/normalizer_parsing_constants.py:24:line_length:111",
    "src/core/drug_matching/normalization/normalizer_parsing_constants.py:25:line_length:109",
    "src/core/drug_matching/normalization/normalizer_parsing_constants.py:26:line_length:109",
    "src/core/drug_matching/normalization/normalizer_parsing_inference.py:22:line_length:108",
    "src/core/drug_matching/normalization/normalizer_parsing_inference.py:29:line_length:111",
    "src/core/drug_matching/normalization/normalizer_parsing_inference.py:35:line_length:175",
    "src/core/drug_matching/normalization/normalizer_parsing_inference.py:37:line_length:171",
    "src/core/drug_matching/normalization/normalizer_parsing_inference.py:39:line_length:134",
    "src/core/drug_matching/normalization/normalizer_parsing_normalize.py:20:function_lines:normalize:31",
    "src/core/drug_matching/normalization/normalizer_parsing_parse.py:104:line_length:125",
    "src/core/drug_matching/normalization/normalizer_parsing_parse.py:118:line_length:135",
    "src/core/drug_matching/normalization/normalizer_parsing_parse.py:121:function_lines:_canonical_form:22",
    "src/core/drug_matching/normalization/normalizer_parsing_parse.py:44:function_lines:parse_drug:75",
    "src/core/drug_matching/normalization/normalizer_parsing_parse.py:91:line_length:162",
    "src/core/drug_matching/normalization/normalizer_parsing_parse.py:file_lines:142",
    "src/core/drug_matching/verification/verifier_helpers.py:fallback_from_unparseable_response:docstring",
    "src/core/drug_matching/verification/verifier_core.py:file_lines:202",
    "src/core/drug_matching/verification/verifier_helpers.py:file_lines:333",
    "src/core/drug_matching/verification/verifier_methods.py:21:function_lines:verify_one:40",
    "src/core/drug_matching/verification/verifier_methods.py:58:line_length:106",
    "src/core/drug_matching/verification/verifier_methods.py:62:function_lines:verify_batch:24",
    "src/core/drug_matching/verification/verifier_request.py:file_lines:206",
    "src/core/drug_matching/verification/verifier_request_build.py:file_lines:179",
    "src/core/drug_matching/verification/verifier_request_parse.py:file_lines:152",
    "src/core/drug_matching/verification/verifier_response.py:file_lines:215",
    "src/core/drug_matching/verification/verifier.py:file_lines:87",
    "src/core/drug_matching/verification/verifier_request_validate.py:file_lines:52",
    "src/core/drug_matching/verification/verifier_search.py:file_lines:92",
    "src/core/drug_matching/verification/verifier_core_extract.py:file_lines:117",
    "src/core/drug_matching/verification/verifier_core_format.py:file_lines:68",
    "src/core/drug_matching/verification/verifier_review.py:122:function_lines:review_batch:28",
    "src/core/drug_matching/verification/verifier_review.py:21:function_lines:review_one:100",
    "src/core/drug_matching/verification/verifier_review.py:77:line_length:106",
    "src/core/drug_matching/verification/verifier_review.py:file_lines:149",
    "src/core/drug_matching/verification/verifier_search.py:20:function_lines:find_better_match:73",
    "src/core/drug_matching/verification/verifier_search.py:file_lines:92",
    "src/core/manual_review_helpers.py:18:line_length:115",
    "src/core/manual_review_helpers.py:31:line_length:138",
    "src/core/manual_review_helpers.py:36:line_length:131",
    "src/core/manual_review_helpers.py:file_lines:123",
    "src/core/manual_review_runtime.py:85:function_lines:filter_manual_review_candidates:21",
    "src/core/manual_review_runtime.py:file_lines:137",
    "src/core/manual_review_store.py:file_lines:142",
    "src/core/matching_risk.py:32:line_length:129",
    "src/core/matching_risk.py:92:line_length:108",
    "src/core/matching_risk.py:96:line_length:102",
    "src/core/matching_risk.py:is_aggressive_flagged_decision:docstring",
    "src/core/matching_trace.py:file_lines:136",
    "src/core/matching_types.py:file_lines:130",
    "src/core/order_ai_flow.py:101:line_length:102",
    "src/core/order_ai_flow.py:50:line_length:109",
    "src/core/order_ai_flow.py:53:line_length:103",
    "src/core/order_ai_flow.py:98:line_length:103",
    "src/core/order_ai_flow.py:file_lines:255",
    "src/core/ordering/order_ai_matching.py:66:line_length:111",
    "src/core/ordering/order_ai_matching.py:file_lines:208",
    "src/core/ordering/order_run_artifact_rows.py:144:function_lines:order_item_summary_row:21",
    "src/core/ordering/order_run_artifact_rows.py:file_lines:269",
    "src/core/matching/product_matching_acceptance.py:file_lines:361",
    "src/core/matching/product_matching_decisions.py:file_lines:236",
    "src/core/matching/product_matching_helpers.py:file_lines:140",
    "src/core/matching/product_matching_numeric.py:file_lines:107",
    "src/core/matching/product_matching_queries.py:41:line_length:108",
    "src/core/matching/product_matching_scoring.py:191:function_lines:_breakdown_from_components:30",
    "src/core/matching/product_matching_scoring.py:file_lines:327",
    "src/core/quality/quality_metrics.py:file_lines:152",
    "src/tawreed/api/tawreed_api_client.py:8:line_length:117",
    "src/tawreed/api/tawreed_api_client.py:file_lines:113",
    "src/tawreed/api/tawreed_api_contract.py:74:line_length:110",
    "src/tawreed/api/tawreed_api_contract.py:77:line_length:257",
    "src/tawreed/api/tawreed_api_contract.py:file_lines:419",
    "src/tawreed/api/tawreed_api_discovery_enhanced.py:file_lines:156",
    "src/tawreed/api/tawreed_api_flow.py:146:function_lines:_select_stores_and_add_to_cart:24",
    "src/tawreed/api/tawreed_api_flow.py:245:function_lines:require_api_match:28",
    "src/tawreed/api/tawreed_api_flow.py:266:line_length:104",
    "src/tawreed/api/tawreed_api_flow.py:268:line_length:109",
    "src/tawreed/api/tawreed_api_flow.py:368:line_length:110",
    "src/tawreed/api/tawreed_api_flow.py:369:line_length:109",
    "src/tawreed/api/tawreed_api_flow.py:372:line_length:153",
    "src/tawreed/api/tawreed_api_flow.py:373:line_length:144",
    "src/tawreed/api/tawreed_api_flow.py:file_lines:420",
    "src/tawreed/api/tawreed_api_matching.py:114:line_length:110",
    "src/tawreed/api/tawreed_api_matching.py:115:line_length:109",
    "src/tawreed/api/tawreed_api_matching.py:118:line_length:153",
    "src/tawreed/api/tawreed_api_matching.py:119:line_length:144",
    "src/tawreed/api/tawreed_api_matching.py:30:line_length:104",
    "src/tawreed/api/tawreed_api_matching.py:32:line_length:109",
    "src/tawreed/api/tawreed_api_matching.py:file_lines:144",
    "src/tawreed/api/tawreed_api_operations.py:file_lines:140",
    "src/tawreed/tawreed_artifacts_io.py:file_lines:214",
    "src/tawreed/tawreed_auth.py:file_lines:169",
    "src/tawreed/tawreed_auto_auth.py:31:line_length:113",
    "src/tawreed/tawreed_auto_auth.py:44:line_length:110",
    "src/tawreed/tawreed_bot_core.py:28:function_lines:__init__:49",
    "src/tawreed/tawreed_bot_methods.py:104:line_length:113",
    "src/tawreed/tawreed_bot_methods.py:file_lines:116",
    "src/tawreed/tawreed_cart_flow.py:24:function_lines:remove_cart_items:26",
    "src/tawreed/tawreed_cart_flow.py:file_lines:106",
    "src/tawreed/tawreed_dom.py:file_lines:177",
    "src/tawreed/tawreed_headless_auth_refresh.py:29:function_lines:_run_auth_refresh_session:23",
    "src/tawreed/tawreed_headless_auth_refresh.py:capture_headless_state:docstring",
    "src/tawreed/tawreed_headless_auth_refresh.py:file_lines:101",
    "src/tawreed/tawreed_headless_auth_refresh.py:products_page_url:docstring",
    "src/tawreed/tawreed_headless_auth_refresh.py:require_env_credentials:docstring",
    "src/tawreed/tawreed_match_only.py:160:line_length:108",
    "src/tawreed/tawreed_match_only.py:file_lines:204",
    "src/tawreed/tawreed_order_flow.py:122:line_length:101",
    "src/tawreed/tawreed_order_flow.py:194:line_length:101",
    "src/tawreed/tawreed_order_flow.py:1:line_length:128",
    "src/tawreed/tawreed_order_flow.py:349:line_length:118",
    "src/tawreed/tawreed_order_flow.py:351:line_length:103",
    "src/tawreed/tawreed_order_flow.py:353:line_length:124",
    "src/tawreed/tawreed_order_flow.py:485:line_length:114",
    "src/tawreed/tawreed_order_flow.py:487:line_length:103",
    "src/tawreed/tawreed_order_flow.py:489:line_length:120",
    "src/tawreed/tawreed_order_flow.py:71:function_lines:place_order_from_items:36",
    "src/tawreed/tawreed_order_flow.py:file_lines:515",
    "src/tawreed/tawreed_order_processing.py:file_lines:159",
    "src/tawreed/tawreed_order_summary.py:100:line_length:176",
    "src/tawreed/tawreed_order_summary.py:104:line_length:102",
    "src/tawreed/tawreed_order_summary.py:10:line_length:104",
    "src/tawreed/tawreed_order_summary.py:25:line_length:154",
    "src/tawreed/tawreed_order_summary.py:45:line_length:173",
    "src/tawreed/tawreed_order_summary.py:50:line_length:116",
    "src/tawreed/tawreed_order_summary.py:53:line_length:117",
    "src/tawreed/tawreed_order_summary.py:57:line_length:116",
    "src/tawreed/tawreed_order_summary.py:file_lines:377",
    "src/tawreed/tawreed_pricing.py:34:line_length:112",
    "src/tawreed/tawreed_product_export.py:file_lines:588",
    "src/tawreed/tawreed_product_search.py:file_lines:114",
    "src/tawreed/tawreed_search_logic.py:26:line_length:114",
    "src/tawreed/tawreed_search_logic.py:34:line_length:126",
    "src/tawreed/tawreed_search_logic.py:41:line_length:125",
    "src/tawreed/tawreed_search_logic.py:file_lines:141",
    "src/tawreed/tawreed_session.py:291:function_lines:validate_saved_session:25",
    "src/tawreed/tawreed_store_selection.py:23:line_length:201",
    "src/tawreed/tawreed_store_selection.py:26:line_length:175",
    "src/tawreed/tawreed_store_selection.py:28:line_length:302",
    "src/tawreed/tawreed_store_selection.py:30:line_length:105",
    "src/tawreed/tawreed_store_selection.py:52:line_length:101",
    "src/tawreed/tawreed_store_selection.py:53:line_length:261",
    "src/tawreed/tawreed_summary.py:file_lines:219",
    "src/ui/streamlit_headless_auth.py:33:line_length:106",
    "src/ui/streamlit_main.py:15:line_length:133",
    "src/ui/streamlit_main.py:77:function_lines:render_main_tabs:23",
    "src/ui/streamlit_main.py:file_lines:107",
    "src/ui/streamlit_manual_review.py:file_lines:374",
    "src/ui/streamlit_manual_review_cli.py:78:line_length:106",
    "src/ui/streamlit_manual_review_page.py:155:line_length:152",
    "src/ui/streamlit_manual_review_page.py:file_lines:406",
    "src/ui/streamlit_manual_review_page_saved.py:107:line_length:113",
    "src/ui/streamlit_manual_review_page_saved.py:file_lines:140",
    "src/ui/streamlit_order.py:105:function_lines:start_order_process:21",
    "src/ui/streamlit_order.py:179:function_lines:order_command:25",
    "src/ui/streamlit_order.py:22:function_lines:render_order_tab:25",
    "src/ui/streamlit_order.py:67:function_lines:render_running_order_controls:36",
    "src/ui/streamlit_order.py:file_lines:203",
    "src/ui/streamlit_overview.py:69:function_lines:render_input_files_table:24",
    "src/ui/streamlit_overview.py:file_lines:112",
    "src/ui/streamlit_process.py:16:line_length:111",
    "src/ui/streamlit_process.py:26:function_lines:start_cli_subprocess:22",
    "src/ui/streamlit_process.py:file_lines:134",
    "src/ui/streamlit_remove_cart.py:132:function_lines:render_running_remove_cart_controls:29",
    "src/ui/streamlit_remove_cart.py:35:function_lines:remove_cart_form_values:26",
    "src/ui/streamlit_remove_cart.py:file_lines:191",
    "src/ui/streamlit_remove_cart.py:308:function_lines:_render_completed_remove_cart:21",
    "src/ui/streamlit_results.py:file_lines:139",
    "src/core/drug_matching/ai_rotation.py:92:function_lines:_provider_attempts:23",
    "src/core/drug_matching/ai_rotation.py:AIModelAttempt:docstring",
    "src/core/drug_matching/ai_rotation.py:configured_attempts:docstring",
    "src/core/drug_matching/ai_rotation.py:file_lines:154",
    "src/core/drug_matching/ai_rotation.py:rank_attempts:docstring",
    "src/core/drug_matching/pipeline.py:177:function_lines:load_data:31",
    "src/core/drug_matching/pipeline.py:253:function_lines:_make_row:27",
    "src/core/drug_matching/pipeline.py:357:function_lines:print_stats:26",
    "src/core/drug_matching/pipeline.py:file_lines:434",
    "src/core/drug_matching/prompts.py:59:line_length:172",
    "src/core/drug_matching/prompts.py:render_prompt:docstring",
    "src/core/drug_matching/trace_log.py:file_lines:116",
    "src/core/prevented_items.py:file_lines:207",
    "src/core/utils/excel.py:file_lines:237",
    "src/tawreed/selectors.py:file_lines:134",
    "src/tawreed/tawreed_artifacts.py:file_lines:163",
    "src/tawreed/tawreed_cart_removal.py:file_lines:224",
    "src/tawreed/tawreed_match_logs.py:335:function_lines:append_order_result_summary:38",
    "src/tawreed/tawreed_products_flow.py:154:function_lines:add_item_from_store_dialogs:39",
    "src/tawreed/tawreed_strategy.py:99:line_length:102",
    "src/tawreed/tawreed_strategy.py:file_lines:115",
    "src/ui/streamlit_order.py:384:function_lines:_render_running_order:21",
    "src/ui/streamlit_order.py:407:function_lines:_render_completed_order:22",
    "src/ui/streamlit_overview.py:22:line_length:104",
    "src/ui/streamlit_overview.py:52:line_length:121",
    "src/ui/streamlit_overview.py:53:line_length:115",
    "src/ui/streamlit_overview.py:61:line_length:116",
    "src/ui/streamlit_overview.py:62:line_length:119",
    "src/ui/streamlit_prevented_items.py:22:function_lines:render_prevented_items_manager:28",
    "src/ui/streamlit_prevented_items.py:73:function_lines:render_prevented_items_editor:40",
    "src/ui/streamlit_prevented_items.py:file_lines:143",
    "src/ui/streamlit_product_matching.py:195:function_lines:render_product_matching_tab:23",
    "src/ui/streamlit_product_matching.py:21:function_lines:product_matching_form:35",
    "src/ui/streamlit_product_matching.py:69:function_lines:product_matching_command:27",
    "src/ui/streamlit_product_matching.py:file_lines:220",
    "src/ui/streamlit_profile_fields.py:37:line_length:171",
    "src/ui/streamlit_profile_fields.py:40:line_length:119",
    "src/ui/streamlit_profile_fields.py:42:line_length:181",
    "src/ui/streamlit_timing.py:76:line_length:117",
    "src/ui/streamlit_timing.py:78:line_length:229",
    "src/ui/streamlit_timing.py:81:line_length:135",
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
