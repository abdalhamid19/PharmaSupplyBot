"""Playwright automation for product search and Tawreed ordering."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from .config_models import AppConfig, ProfileConfig
from .excel import Item
from .product_matching import (
    CandidateMatchDiagnostic,
    MatchDecision,
    _SearchMatch,
    _search_queries_for_item,
    explain_best_product_match,
    find_best_product_match,
    is_decisive_product_match,
)
from .selectors import _selectors
from .tawreed_artifacts import (
    append_csv_artifact,
    append_text_artifact,
    dump_artifacts,
    write_text_artifact,
)
from .tawreed_navigation import go_to_orders, maybe_switch_pharmacy, start_new_order
from .tawreed_session import (
    attempt_env_login,
    close_browser,
    close_context,
    ensure_logged_in,
    open_auth_page,
    open_order_page,
    print_auth_instructions,
    print_login_detection_result,
    save_session_state,
    wait_for_login_detection,
    wait_for_network_idle,
)
from .tawreed_strategy import choose_store_index, max_available_warehouse_row
from .tawreed_ui import (
    bounded_requested_quantity,
    cart_button,
    checkout_confirmation_labels,
    dialog_footer_buttons,
    fill_quantity_input,
    store_dialog_cart_buttons,
    stores_button,
    visible_dialog,
)


class _SkipItem(Exception):
    """Signal that one item should be skipped without failing the whole order run."""

    pass


class TawreedBot:
    """Coordinate Tawreed authentication, product matching, and order placement."""

    def __init__(
        self,
        config: AppConfig,
        profile_key: str,
        profile: ProfileConfig,
        state_path: Path,
    ):
        """Create a bot instance bound to one Tawreed profile and saved session state."""
        self.config = config
        self.profile_key = profile_key
        self.profile = profile
        self.state_path = state_path
        self.selectors = _selectors(config)

    def auth_interactive(self, wait_seconds: int = 600) -> None:
        """Open a visible browser and persist session state after manual login."""
        with sync_playwright() as p:
            browser, context, page = open_auth_page(p, self.config.base_url, self.config.runtime)
            attempt_env_login(page, self.selectors)
            print_auth_instructions(wait_seconds)
            detected = wait_for_login_detection(
                page,
                context,
                wait_seconds,
                self.selectors.logged_in_marker,
                self.state_path,
            )
            wait_for_network_idle(page)
            print_login_detection_result(detected)
            save_session_state(context, self.state_path, is_intermediate=False)
            browser.close()
            print(f"Saved session state: {self.state_path}")

    def place_order_from_items(self, items: list[Item]) -> None:
        """Place an order by processing each item from the provided list."""
        with sync_playwright() as p:
            browser, context, page = open_order_page(p, self.config.runtime, self.state_path)
            try:
                self._prepare_order_page(page)
                self._process_items(page, items)
                self._confirm_order(page)
            except Exception as e:
                dump_artifacts(page, self.profile_key, label="order_flow_error")
                raise
            finally:
                close_context(context)
                close_browser(browser)

    def _prepare_order_page(self, page: Page) -> None:
        """Open the site and navigate to the ordering surface for item processing."""
        page.goto(self._products_page_url(), wait_until="domcontentloaded")
        self._ensure_logged_in(page)
        maybe_switch_pharmacy(page, self.profile.pharmacy_switch or {})
        if self._order_surface_ready(page):
            return
        go_to_orders(page, self.selectors.go_to_orders, self._order_surface_selector())
        start_new_order(page, self.selectors.new_order, self.selectors.item_search_input)

    def _process_items(self, page: Page, items: list[Item]) -> None:
        """Process each requested Excel item on the current order page."""
        for item in items:
            self._process_single_item(page, item)

    def _order_surface_selector(self) -> str:
        """Return the selector that best indicates the order surface is ready."""
        if self.selectors.new_order:
            return self.selectors.new_order
        return self.selectors.item_search_input

    def _products_page_url(self) -> str:
        """Return the direct Tawreed products page URL for faster order startup."""
        if "#/" in self.config.base_url:
            origin, _ = self.config.base_url.split("#/", 1)
            return f"{origin}#/catalog/store-products/dv/"
        return self.config.base_url

    def _order_surface_ready(self, page: Page) -> bool:
        """Return whether the products ordering surface is already interactive."""
        try:
            page.locator(self.selectors.item_search_input).first.wait_for(timeout=1500)
            return True
        except Exception:
            return False

    def _process_single_item(self, page: Page, item: Item) -> None:
        """Add one item or save artifacts when a technical failure happens."""
        try:
            self._add_item(page, item)
        except _SkipItem as error:
            print(f"[{self.profile_key}] Skipped item {item.code} / {item.name}: {error}")
        except Exception as error:
            print(f"[{self.profile_key}] Failed item {item.code} / {item.name}: {error}")
            dump_artifacts(page, self.profile_key, label=f"item_error_{item.code or 'no_code'}")

    def _ensure_logged_in(self, page: Page) -> None:
        """Verify that the saved session is still authenticated before ordering begins."""
        ensure_logged_in(
            page,
            self.selectors,
            self.config.runtime.timeout_ms,
            ready_selector=self.selectors.item_search_input,
        )

    def _add_item(self, page: Page, item: Item) -> None:
        """Add one item using either the products-page flow or the legacy configured flow."""
        if self.selectors.item_search_input == "#tawreedTableGlobalSearch":
            self._add_item_from_products_page(page, item)
            return

        self._add_item_with_configured_flow(page, item)

    def _add_item_with_configured_flow(self, page: Page, item: Item) -> None:
        """Execute the selector-driven fallback flow for non-products ordering pages."""
        search = page.locator(self.selectors.item_search_input).first
        search.click()
        search.fill("")
        query = item.code if item.code else item.name
        search.fill(query)

        self._pick_configured_search_result(page, search)
        self._fill_configured_quantity(page, item.qty)
        page.locator(self.selectors.add_item_button).first.click()
        self._wait_for_legacy_add_completion(page)

    def _pick_configured_search_result(self, page: Page, search) -> None:
        """Select the configured search result when that selector exists."""
        if not self.selectors.item_first_result:
            return
        try:
            page.locator(self.selectors.item_first_result).first.wait_for(timeout=5000)
            page.locator(self.selectors.item_first_result).first.click()
        except Exception:
            search.press("Enter")

    def _fill_configured_quantity(self, page: Page, quantity: int) -> None:
        """Fill the configured quantity input when that selector exists."""
        if not self.selectors.qty_input:
            return
        quantity_input = page.locator(self.selectors.qty_input).first
        quantity_input.fill("")
        quantity_input.fill(str(quantity))

    def _add_item_from_products_page(self, page: Page, item: Item) -> None:
        """Add one item using the Tawreed products page search-and-store selection flow."""
        match, active_query = self._require_product_match(page, item)
        row = self._matched_product_row(page, match, active_query)
        self._open_add_to_cart_for_match(page, row, item, match)
        self._fill_add_to_cart_dialog(page, item.qty)

    def _visible_product_rows(self, page: Page):
        """Return the rendered product rows in the current products table."""
        return page.locator("tbody.p-datatable-tbody > tr")

    def _search_products(self, page: Page, query: str) -> list[dict[str, Any]]:
        """Search the products table and return the parsed API results for the query."""
        search = page.locator(self.selectors.item_search_input).first
        search.click()
        search.fill("")
        search.fill(query)

        with page.expect_response(
            self._is_product_search_response,
            timeout=self.config.runtime.timeout_ms,
        ) as resp_info:
            search.press("Enter")

        payload = resp_info.value.json()
        self._wait_for_product_rows(page)
        return list(payload.get("data", {}).get("content", []) or [])

    def _find_best_product_match(self, page: Page, item: Item) -> tuple[MatchDecision, str | None]:
        """Search all candidate queries and return diagnostics plus the active query."""
        search_results_by_query: list[tuple[str, list[dict[str, Any]]]] = []
        for query in _search_queries_for_item(item):
            results = self._search_products(page, query)
            search_results_by_query.append((query, results))
            decision = explain_best_product_match(
                item,
                search_results_by_query,
                self.config.matching,
            )
            if (
                decision.best_match
                and is_decisive_product_match(
                    item.name or query,
                    decision.best_match.data,
                )
            ):
                self._write_match_log(item, decision)
                return decision, query
        active_query = search_results_by_query[-1][0] if search_results_by_query else None
        decision = explain_best_product_match(item, search_results_by_query, self.config.matching)
        self._write_match_log(item, decision)
        return decision, active_query

    def _require_product_match(self, page: Page, item: Item) -> tuple[_SearchMatch, str | None]:
        """Require a valid product match or raise a descriptive runtime error."""
        decision, active_query = self._find_best_product_match(page, item)
        if decision.best_match:
            return decision.best_match, active_query
        raise RuntimeError(f"No matching product found for '{item.name}' (code: {item.code}).")

    def _matched_product_row(self, page: Page, match: _SearchMatch, active_query: str | None):
        """Re-run the winning query and return the visible row that corresponds to the match."""
        if active_query != match.query:
            self._search_products(page, match.query)
        rows = self._visible_product_rows(page)
        if rows.count() <= match.row_index:
            raise RuntimeError(self._missing_row_message(match))

        row = rows.nth(match.row_index)
        if self._is_no_results_row(row):
            raise RuntimeError(f"No results found for '{match.query}'.")
        return row

    def _missing_row_message(self, match: _SearchMatch) -> str:
        """Build the error shown when a matched row disappears from the rendered table."""
        return (
            f"Matched row index {match.row_index} is not visible after searching for "
            f"'{match.query}'."
        )

    def _is_no_results_row(self, row) -> bool:
        """Return whether the current table row is Tawreed's no-results placeholder."""
        return "No results found" in row.inner_text()

    def _wait_for_product_rows(self, page: Page) -> None:
        """Wait until the products table renders at least one visible row."""
        try:
            self._visible_product_rows(page).first.wait_for(timeout=2000)
        except Exception:
            pass

    def _open_add_to_cart_for_match(
        self,
        page: Page,
        row,
        item: Item,
        match: _SearchMatch,
    ) -> None:
        """Open the add-to-cart dialog for the selected match and chosen store."""
        if self._match_has_multiple_stores(match):
            self._open_store_cart_dialog(page, row)
            return
        self._click_single_store_cart(row, item, match)

    def _match_has_multiple_stores(self, match: _SearchMatch) -> bool:
        """Return whether the matched product requires store selection first."""
        return int(match.data.get("productsCount") or 0) > 0

    def _open_store_cart_dialog(self, page: Page, row) -> None:
        """Open the stores dialog and click the chosen store cart button."""
        store_rows = self._open_stores_dialog(page, row)
        store_index = choose_store_index(store_rows, self._warehouse_mode(), _SkipItem)
        stores_dialog = visible_dialog(page, self.config.runtime.timeout_ms)
        store_dialog_cart_buttons(stores_dialog).nth(store_index).click()

    def _click_single_store_cart(self, row, item: Item, match: _SearchMatch) -> None:
        """Click the direct cart button for matches that do not require a stores dialog."""
        available_quantity = int(match.data.get("availableQuantity") or 0)
        if available_quantity <= 0:
            raise _SkipItem(f"Matched product is out of stock for '{item.name}'.")
        cart_button(row).click()

    def _is_product_search_response(self, response) -> bool:
        """Return whether a network response belongs to the product search endpoint."""
        return (
            "stores/products/search/similar5" in response.url
            and response.request.method == "POST"
        )

    def _open_stores_dialog(self, page: Page, row) -> list[dict[str, Any]]:
        """Open the stores dialog for a row and return the API payload behind it."""
        with page.expect_response(
            lambda resp: (
                "stores/products/product/get" in resp.url
                and resp.request.method == "POST"
            ),
            timeout=self.config.runtime.timeout_ms,
        ) as resp_info:
            stores_button(row).click()

        response = resp_info.value
        payload = response.json()
        stores = list(payload.get("data", []) or [])
        if not stores:
            raise RuntimeError("Stores dialog opened, but no store rows were returned.")
        return stores

    def _fill_add_to_cart_dialog(self, page: Page, requested_qty: int) -> None:
        """Fill the quantity dialog and submit the add-to-cart action."""
        dialog = visible_dialog(page, self.config.runtime.timeout_ms)
        footer_buttons = dialog_footer_buttons(dialog, self.config.runtime.timeout_ms)
        quantity_input = dialog.locator("input[role='spinbutton']").first
        quantity = bounded_requested_quantity(quantity_input, requested_qty)
        fill_quantity_input(quantity_input, quantity)
        footer_buttons.last.click()
        try:
            dialog.wait_for(state="hidden", timeout=1500)
        except Exception:
            pass

    def _pick_warehouse_if_needed(self, page: Page) -> None:
        """Pick a warehouse row from a warehouse chooser when that flow is active."""
        mode = self._warehouse_mode()
        rows = page.locator(self.selectors.warehouse_rows)
        if rows.count() == 0:
            return

        if mode == "first_available":
            self._click_warehouse_row(page, rows.first)
            return

        if mode == "max_available":
            row_index = max_available_warehouse_row(rows, self.selectors.warehouse_available_qty)
            self._click_warehouse_row(page, rows.nth(row_index))
            return

        raise ValueError(f"Unknown warehouse strategy mode: {mode}")

    def _warehouse_mode(self) -> str:
        """Return the configured warehouse-selection mode."""
        return str(self.config.warehouse_strategy.get("mode", "first_available"))

    def _click_warehouse_row(self, page: Page, row) -> None:
        """Click the warehouse pick button for the provided row."""
        row.locator(self.selectors.warehouse_pick_button).first.click()
        self._wait_for_warehouse_selection(page)

    def _confirm_order(self, page: Page) -> None:
        """Click all enabled checkout buttons and confirm any resulting dialogs."""
        if not self.selectors.confirm_order_button:
            return
        checkout_buttons = self._checkout_candidates(page)
        checkout_count = checkout_buttons.count()
        if checkout_count == 0:
            self._print_no_checkout_buttons_message()
            return

        for checkout_index in range(checkout_count):
            button = checkout_buttons.nth(checkout_index)
            try:
                self._click_checkout_button(button, page)
                self._confirm_checkout_dialog(page)
            except Exception as error:
                print(
                    f"[{self.profile_key}] Checkout click failed on button "
                    f"{checkout_index + 1}/{checkout_count}: {error}"
                )

    def _print_no_checkout_buttons_message(self) -> None:
        """Print the message used when no checkout button is currently actionable."""
        print(
            f"[{self.profile_key}] No enabled Checkout buttons found "
            "(cart may be empty, out of stock, or below minimum order)."
        )

    def _checkout_candidates(self, page: Page):
        """Return checkout buttons that appear to be enabled for submission."""
        configured_buttons = page.locator(self.selectors.confirm_order_button)
        enabled_buttons = configured_buttons.filter(has_not=page.locator("[disabled]"))
        enabled_checkout_text = page.locator("button:has-text('Checkout'):not([disabled])")
        if enabled_checkout_text.count() > 0:
            return enabled_checkout_text
        return enabled_buttons

    def _click_checkout_button(self, button, page: Page) -> None:
        """Click a checkout button, retrying with force if overlays intercept it."""
        try:
            button.click(timeout=5000)
        except Exception:
            button.click(timeout=5000, force=True)
        self._wait_for_checkout_dialog(page)

    def _confirm_checkout_dialog(self, page: Page) -> None:
        """Confirm the visible checkout dialog using known multilingual labels."""
        dialog = self._visible_checkout_dialog(page)
        if dialog.count() == 0:
            return
        for label in checkout_confirmation_labels():
            confirm_button = dialog.locator(f"button:has-text('{label}')")
            if confirm_button.count() == 0:
                continue
            try:
                confirm_button.first.click(timeout=3000)
                self._wait_for_checkout_completion(dialog, page)
                return
            except Exception:
                pass

    def _wait_for_checkout_dialog(self, page: Page) -> None:
        """Wait briefly for a checkout confirmation dialog to appear."""
        try:
            self._visible_checkout_dialog(page).first.wait_for(timeout=1200)
        except Exception:
            pass

    def _visible_checkout_dialog(self, page: Page):
        """Return the visible checkout dialog locator."""
        return page.locator(".p-dialog:visible")

    def _wait_for_checkout_completion(self, dialog, page: Page) -> None:
        """Wait for the checkout confirmation dialog to close after submission."""
        try:
            dialog.first.wait_for(state="hidden", timeout=1500)
            return
        except Exception:
            pass
        try:
            page.wait_for_load_state("domcontentloaded", timeout=1000)
        except Exception:
            pass

    def _wait_for_legacy_add_completion(self, page: Page) -> None:
        """Wait briefly for the legacy add-item flow to settle after submission."""
        try:
            page.locator(self.selectors.item_search_input).first.wait_for(timeout=1000)
        except Exception:
            pass

    def _wait_for_warehouse_selection(self, page: Page) -> None:
        """Wait briefly for the warehouse chooser to settle after selecting a row."""
        try:
            page.locator(self.selectors.warehouse_rows).first.wait_for(state="hidden", timeout=1000)
        except Exception:
            pass

    def _write_match_log(self, item: Item, decision: MatchDecision) -> None:
        """Write a detailed product-matching log for the current item."""
        log_content = self._match_log_content(item, decision)
        log_label = f"match_log_{self._safe_item_label(item)}"
        write_text_artifact(self.profile_key, log_label, log_content)
        append_text_artifact(
            self.profile_key,
            "match_log_all",
            self._match_log_section_separator(item) + log_content,
        )
        append_csv_artifact(
            self.profile_key,
            "match_log_all",
            self._match_log_csv_rows(item, decision),
        )

    def _match_log_content(self, item: Item, decision: MatchDecision) -> str:
        """Build the detailed product-matching log content for one item."""
        lines = [
            f"item_code={item.code}",
            f"item_name={item.name}",
            f"item_qty={item.qty}",
            f"final_reason={decision.final_reason}",
            f"best_match_query={decision.best_match.query if decision.best_match else ''}",
            f"best_match_row_index={decision.best_match.row_index if decision.best_match else ''}",
            f"best_match_score={decision.best_match.score if decision.best_match else ''}",
            "",
            "candidates:",
        ]
        for candidate_index, diagnostic in enumerate(
            sorted(decision.diagnostics, key=lambda current: current.sort_key, reverse=True),
            start=1,
        ):
            lines.extend(self._candidate_log_lines(candidate_index, diagnostic))
        return "\n".join(lines) + "\n"

    def _candidate_log_lines(
        self,
        candidate_index: int,
        diagnostic: CandidateMatchDiagnostic,
    ) -> list[str]:
        """Build the log lines for one candidate considered during matching."""
        breakdown = diagnostic.breakdown
        candidate_name_en = str(diagnostic.candidate.get("productNameEn") or "")
        candidate_name_ar = str(diagnostic.candidate.get("productName") or "")
        return [
            f"- candidate_{candidate_index}:",
            f"  query={diagnostic.query}",
            f"  row_index={diagnostic.row_index}",
            f"  product_name_en={candidate_name_en}",
            f"  product_name_ar={candidate_name_ar}",
            f"  available_quantity={diagnostic.candidate.get('availableQuantity')}",
            f"  products_count={diagnostic.candidate.get('productsCount')}",
            f"  store_product_id={diagnostic.candidate.get('storeProductId')}",
            f"  total_score={diagnostic.score:.3f}",
            f"  sequence_score={breakdown.sequence_score:.3f}",
            f"  overlap_score={breakdown.overlap_score:.3f}",
            f"  numeric_overlap={breakdown.numeric_overlap:.3f}",
            f"  exact_bonus={breakdown.exact_bonus:.3f}",
            f"  availability_bonus={breakdown.availability_bonus:.3f}",
            f"  sort_key={diagnostic.sort_key}",
            f"  accepted={diagnostic.accepted}",
            f"  accepted_reason={diagnostic.accepted_reason}",
            f"  rejection_reason={diagnostic.rejection_reason}",
            "",
        ]

    def _match_log_csv_rows(self, item: Item, decision: MatchDecision) -> list[dict[str, object]]:
        """Build CSV rows for all candidates considered during item matching."""
        rows: list[dict[str, object]] = []
        for rank, diagnostic in enumerate(
            sorted(decision.diagnostics, key=lambda current: current.sort_key, reverse=True),
            start=1,
        ):
            breakdown = diagnostic.breakdown
            rows.append(
                {
                    "item_code": item.code,
                    "item_name": item.name,
                    "item_qty": item.qty,
                    "final_reason": decision.final_reason,
                    "best_match_query": decision.best_match.query if decision.best_match else "",
                    "best_match_row_index": (
                        decision.best_match.row_index
                        if decision.best_match
                        else ""
                    ),
                    "best_match_score": decision.best_match.score if decision.best_match else "",
                    "candidate_rank": rank,
                    "query": diagnostic.query,
                    "row_index": diagnostic.row_index,
                    "product_name_en": str(diagnostic.candidate.get("productNameEn") or ""),
                    "product_name_ar": str(diagnostic.candidate.get("productName") or ""),
                    "available_quantity": diagnostic.candidate.get("availableQuantity"),
                    "products_count": diagnostic.candidate.get("productsCount"),
                    "store_product_id": diagnostic.candidate.get("storeProductId"),
                    "total_score": round(diagnostic.score, 6),
                    "sequence_score": round(breakdown.sequence_score, 6),
                    "overlap_score": round(breakdown.overlap_score, 6),
                    "numeric_overlap": round(breakdown.numeric_overlap, 6),
                    "exact_bonus": round(breakdown.exact_bonus, 6),
                    "availability_bonus": round(breakdown.availability_bonus, 6),
                    "sort_key": str(diagnostic.sort_key),
                    "accepted": diagnostic.accepted,
                    "accepted_reason": diagnostic.accepted_reason,
                    "rejection_reason": diagnostic.rejection_reason,
                }
            )
        return rows

    def _safe_item_label(self, item: Item) -> str:
        """Return a filesystem-safe label for item-specific artifacts."""
        item_code = str(item.code or "no_code").strip().replace(" ", "_")
        safe_label = "".join(
            character
            for character in item_code
            if character.isalnum() or character in {"_", "-"}
        )
        return safe_label or "no_code"

    def _match_log_section_separator(self, item: Item) -> str:
        """Return the section separator used inside the aggregated match log."""
        return (
            "\n"
            + "=" * 80
            + "\n"
            + f"item_code={item.code} | item_name={item.name}\n"
            + "=" * 80
            + "\n"
        )
