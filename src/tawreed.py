from __future__ import annotations

import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

from .config import AppConfig, ProfileConfig
from .excel import Item


@dataclass(frozen=True)
class _Sel:
    login_email: str
    login_password: str
    login_submit: str
    logged_in_marker: str

    go_to_orders: str
    new_order: str
    item_search_input: str
    item_first_result: str
    qty_input: str
    add_item_button: str
    confirm_order_button: str

    warehouse_rows: str
    warehouse_available_qty: str
    warehouse_pick_button: str


@dataclass(frozen=True)
class _SearchMatch:
    query: str
    row_index: int
    score: float
    data: dict[str, Any]


class _SkipItem(Exception):
    pass


def _get(d: dict[str, Any], *keys: str, default: str = "") -> str:
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return str(cur)


def _normalize_text(value: str) -> str:
    txt = str(value or "").upper()
    txt = re.sub(r"(?<=\d)(?=[A-Z])|(?<=[A-Z])(?=\d)", " ", txt)
    txt = re.sub(r"[^A-Z0-9]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _token_overlap_score(query: str, candidate: str) -> float:
    q_tokens = _normalize_text(query).split()
    c_tokens = _normalize_text(candidate).split()
    if not q_tokens or not c_tokens:
        return 0.0

    total = 0.0
    for q in q_tokens:
        best = 0.0
        for c in c_tokens:
            if q == c:
                best = 1.0
                break
            if q in c or c in q:
                best = max(best, 0.7)
        total += best
    return total / len(q_tokens)


def _match_score(query: str, candidate: dict[str, Any]) -> float:
    product_name_en = str(candidate.get("productNameEn") or "")
    product_name = str(candidate.get("productName") or "")
    normalized_query = _normalize_text(query)
    normalized_en = _normalize_text(product_name_en)
    normalized_ar = _normalize_text(product_name)

    texts = [t for t in (normalized_en, normalized_ar) if t]
    if not texts:
        return -999.0

    seq = max(SequenceMatcher(None, normalized_query, text).ratio() for text in texts)
    overlap = max(_token_overlap_score(query, text) for text in texts)

    query_numeric = {tok for tok in _normalize_text(query).split() if any(ch.isdigit() for ch in tok)}
    numeric_overlap = 0.0
    if query_numeric:
        numeric_scores: list[float] = []
        for text in texts:
            text_numeric = {tok for tok in text.split() if any(ch.isdigit() for ch in tok)}
            numeric_scores.append(len(query_numeric & text_numeric) / max(1, len(query_numeric)))
        numeric_overlap = max(numeric_scores)

    score = (seq * 5.0) + (overlap * 8.0) + (numeric_overlap * 6.0)

    if normalized_query and any(
        normalized_query == text or normalized_query in text or text in normalized_query for text in texts
    ):
        score += 2.0

    available_qty = int(candidate.get("availableQuantity") or 0)
    products_count = int(candidate.get("productsCount") or 0)
    if available_qty > 0 or products_count > 0 or candidate.get("storeProductId"):
        score += 1.0
    else:
        score -= 1.5

    return score


def _match_sort_key(query: str, candidate: dict[str, Any], score: float) -> tuple[float, int, float, int, int, int]:
    query_norm = _normalize_text(query)
    name_en_norm = _normalize_text(str(candidate.get("productNameEn") or ""))
    exact_name = 1 if query_norm == name_en_norm else 0

    query_numeric = {tok for tok in query_norm.split() if any(ch.isdigit() for ch in tok)}
    name_en_numeric = {tok for tok in name_en_norm.split() if any(ch.isdigit() for ch in tok)}
    numeric_matches = len(query_numeric & name_en_numeric)

    return (
        score,
        exact_name,
        _token_overlap_score(query, str(candidate.get("productNameEn") or "")),
        numeric_matches,
        int(candidate.get("productsCount") or 0),
        int(candidate.get("availableQuantity") or 0),
    )


def _is_match_acceptable(query: str, candidate: dict[str, Any], score: float) -> bool:
    overlap_en = _token_overlap_score(query, str(candidate.get("productNameEn") or ""))
    overlap_ar = _token_overlap_score(query, str(candidate.get("productName") or ""))
    best_overlap = max(overlap_en, overlap_ar)

    query_norm = _normalize_text(query)
    name_en_norm = _normalize_text(str(candidate.get("productNameEn") or ""))
    exact_name = bool(query_norm and query_norm == name_en_norm)

    query_numeric = {tok for tok in query_norm.split() if any(ch.isdigit() for ch in tok)}
    name_numeric = {tok for tok in name_en_norm.split() if any(ch.isdigit() for ch in tok)}
    has_numeric_match = bool(query_numeric and (query_numeric & name_numeric))

    if exact_name:
        return True
    if best_overlap >= 0.85:
        return True
    if score >= 12.0 and best_overlap >= 0.6:
        return True
    if score >= 16.0 and has_numeric_match and best_overlap >= 0.45:
        return True
    return False


def _unique_non_empty(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        v = str(value or "").strip()
        key = v.lower()
        if not v or key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def _selectors(cfg: AppConfig) -> _Sel:
    sel = cfg.selectors
    ws = cfg.warehouse_strategy.get("selectors", {}) if isinstance(cfg.warehouse_strategy, dict) else {}
    return _Sel(
        login_email=_get(sel, "login", "email_input", default="input[type='email']"),
        login_password=_get(sel, "login", "password_input", default="input[type='password']"),
        login_submit=_get(sel, "login", "submit_button", default="button[type='submit']"),
        logged_in_marker=_get(sel, "nav", "logged_in_marker", default="text=Home"),
        go_to_orders=_get(sel, "order_flow", "go_to_orders", default="text=Orders"),
        new_order=_get(sel, "order_flow", "new_order", default="text=New Order"),
        item_search_input=_get(sel, "order_flow", "item_search_input", default="input[placeholder*='Search']"),
        item_first_result=_get(sel, "order_flow", "item_first_result", default=":nth-match(.results *, 1)"),
        qty_input=_get(sel, "order_flow", "qty_input", default="input[type='number']"),
        add_item_button=_get(sel, "order_flow", "add_item_button", default="text=Add"),
        confirm_order_button=_get(sel, "order_flow", "confirm_order_button", default="text=Confirm"),
        warehouse_rows=str(ws.get("warehouse_rows", ".warehouse-row")),
        warehouse_available_qty=str(ws.get("available_qty", ".available")),
        warehouse_pick_button=str(ws.get("pick_button", "text=Select")),
    )


class TawreedBot:
    def __init__(self, cfg: AppConfig, profile_key: str, profile: ProfileConfig, state_path: Path):
        self.cfg = cfg
        self.profile_key = profile_key
        self.profile = profile
        self.state_path = state_path
        self.sel = _selectors(cfg)

    def auth_interactive(self, wait_seconds: int = 600) -> None:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=self.cfg.runtime.slow_mo_ms)
            context = browser.new_context()
            page = context.new_page()
            page.set_default_timeout(self.cfg.runtime.timeout_ms)

            page.goto(self.cfg.base_url, wait_until="domcontentloaded")

            email = os.getenv("TAWREED_EMAIL", "").strip()
            password = os.getenv("TAWREED_PASSWORD", "").strip()
            if email and password:
                try:
                    page.locator(self.sel.login_email).first.fill(email)
                    page.locator(self.sel.login_password).first.fill(password)
                    page.locator(self.sel.login_submit).first.click()
                except Exception:
                    pass

            wait_ms = max(1, int(wait_seconds)) * 1000
            print(
                "Browser opened. Please complete login manually.\n"
                f"- I will keep the browser open for up to {wait_seconds} seconds waiting for login detection.\n"
                "- If the site requires OTP/CAPTCHA, finish it in the browser.\n"
            )

            # Some environments are non-interactive (no stdin). To avoid losing the session,
            # we poll for a "logged-in marker" and ALSO periodically persist storage state.
            detected = False
            total_waited_ms = 0
            poll_ms = 2000
            save_every_ms = 5000
            since_save_ms = 0

            while total_waited_ms < wait_ms and not detected:
                try:
                    page.locator(self.sel.logged_in_marker).first.wait_for(timeout=poll_ms)
                    detected = True
                    break
                except Exception:
                    detected = False

                total_waited_ms += poll_ms
                since_save_ms += poll_ms

                if since_save_ms >= save_every_ms:
                    try:
                        context.storage_state(path=str(self.state_path))
                        print(f"Saved intermediate session state: {self.state_path}")
                    except Exception:
                        pass
                    since_save_ms = 0

            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

            if detected:
                print("Login detected.")
            else:
                print(
                    "Login marker not detected before timeout. Saving session anyway.\n"
                    "If it doesn't work later, update selectors.nav.logged_in_marker in config.yaml."
                )

            context.storage_state(path=str(self.state_path))
            browser.close()
            print(f"Saved session state: {self.state_path}")

    def place_order_from_items(self, items: list[Item]) -> None:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.cfg.runtime.headless, slow_mo=self.cfg.runtime.slow_mo_ms)
            context = browser.new_context(storage_state=str(self.state_path))
            page = context.new_page()
            page.set_default_timeout(self.cfg.runtime.timeout_ms)

            try:
                page.goto(self.cfg.base_url, wait_until="domcontentloaded")
                self._ensure_logged_in(page)
                self._maybe_switch_pharmacy(page)
                self._go_to_orders(page)
                self._start_new_order(page)

                for item in items:
                    try:
                        self._add_item(page, item)
                    except _SkipItem as e:
                        print(f"[{self.profile_key}] Skipped item {item.code} / {item.name}: {e}")
                    except Exception as e:
                        print(f"[{self.profile_key}] Failed item {item.code} / {item.name}: {e}")
                        self._dump_artifacts(page, label=f"item_error_{item.code or 'no_code'}")

                self._confirm_order(page)
            except Exception as e:
                self._dump_artifacts(page, label="order_flow_error")
                raise
            finally:
                try:
                    context.close()
                except Exception:
                    pass
                try:
                    browser.close()
                except Exception:
                    pass

    def _dump_artifacts(self, page: Page, label: str) -> None:
        try:
            artifacts = Path("artifacts") / self.profile_key
            artifacts.mkdir(parents=True, exist_ok=True)
            png = artifacts / f"{label}.png"
            html = artifacts / f"{label}.html"
            txt = artifacts / f"{label}.txt"

            try:
                page.screenshot(path=str(png), full_page=True)
            except Exception:
                pass
            try:
                content = page.content()
                # Make HTML easier to inspect with line-based tools.
                pretty = content.replace("><", ">\n<")
                html.write_text(pretty, encoding="utf-8")
            except Exception:
                pass
            try:
                txt.write_text(f"url={page.url}\n", encoding="utf-8")
            except Exception:
                pass

            print(f"[{self.profile_key}] Saved artifacts to: {artifacts}")
        except Exception:
            pass

    def _ensure_logged_in(self, page: Page) -> None:
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(500)

        # Prefer a configured "logged-in marker", but fall back to "login form is gone".
        # This makes the bot resilient to UI language/label changes.
        timeout_ms = self.cfg.runtime.timeout_ms
        try:
            page.locator(self.sel.logged_in_marker).first.wait_for(timeout=timeout_ms)
            return
        except Exception:
            pass

        try:
            # If we can still see login inputs, we're not logged in.
            login_email_visible = page.locator(self.sel.login_email).first.is_visible(timeout=2000)
            login_pwd_visible = page.locator(self.sel.login_password).first.is_visible(timeout=2000)
            if login_email_visible or login_pwd_visible:
                raise RuntimeError("Still on login page (login inputs visible).")
        except Exception:
            # If visibility checks fail due to selector mismatch, just proceed and let later steps fail
            # with a more actionable selector error.
            return

    def _maybe_switch_pharmacy(self, page: Page) -> None:
        sw = self.profile.pharmacy_switch or {}
        if not sw.get("enabled"):
            return
        name = str(sw.get("pharmacy_name", "")).strip()
        if not name:
            return
        # Placeholder: different tenants implement this differently.
        # Configure selectors in config.yaml if needed for your account.
        page.get_by_text(name, exact=False).first.click(timeout=3000)

    def _go_to_orders(self, page: Page) -> None:
        try:
            page.locator(self.sel.go_to_orders).first.click()
        except Exception:
            # Fallback: sidebar text labels (as seen in captured HTML)
            # User wants Products page, not Purchase Cart.
            try:
                page.get_by_role("link", name="Products").first.click()
            except Exception:
                page.get_by_text("Products", exact=False).first.click()
        page.wait_for_load_state("networkidle")

    def _start_new_order(self, page: Page) -> None:
        # Purchase Cart flow doesn't require creating a new order explicitly.
        if not self.sel.new_order:
            return
        page.locator(self.sel.new_order).first.click()
        page.wait_for_timeout(300)

    def _add_item(self, page: Page, item: Item) -> None:
        if self.sel.item_search_input == "#tawreedTableGlobalSearch":
            self._add_item_from_products_page(page, item)
            return

        search = page.locator(self.sel.item_search_input).first
        search.click()
        search.fill("")
        query = item.code if item.code else item.name
        search.type(query, delay=10)

        if self.sel.item_first_result:
            try:
                page.locator(self.sel.item_first_result).first.wait_for(timeout=5000)
                page.locator(self.sel.item_first_result).first.click()
            except Exception:
                search.press("Enter")
            page.wait_for_timeout(200)

        if self.sel.qty_input:
            qty = page.locator(self.sel.qty_input).first
            qty.fill("")
            qty.type(str(item.qty), delay=5)

        page.locator(self.sel.add_item_button).first.click()
        page.wait_for_timeout(300)

    def _add_item_from_products_page(self, page: Page, item: Item) -> None:
        match = self._find_best_product_match(page, item)
        if not match:
            raise RuntimeError(f"No matching product found for '{item.name}' (code: {item.code}).")

        # Ensure the page is rendered for the winning query before clicking a row.
        self._search_products(page, match.query)
        rows = self._visible_product_rows(page)
        if rows.count() <= match.row_index:
            raise RuntimeError(
                f"Matched row index {match.row_index} is not visible after searching for '{match.query}'."
            )

        row = rows.nth(match.row_index)
        if "No results found" in row.inner_text():
            raise RuntimeError(f"No results found for '{match.query}'.")

        available_qty = int(match.data.get("availableQuantity") or 0)
        products_count = int(match.data.get("productsCount") or 0)

        if products_count > 0:
            store_rows = self._open_stores_dialog(page, row)
            store_index = self._choose_store_index(store_rows)
            stores_dialog = self._visible_dialog(page)
            stores_dialog.locator("button:has-text('Shopping Cart')").nth(store_index).click()
        else:
            if available_qty <= 0:
                raise _SkipItem(f"Matched product is out of stock for '{item.name}'.")
            row.locator("button:has-text('Shopping Cart')").first.click()

        self._fill_add_to_cart_dialog(page, item.qty)
        page.wait_for_timeout(500)

    def _visible_product_rows(self, page: Page):
        return page.locator("tbody.p-datatable-tbody > tr")

    def _search_queries_for_item(self, item: Item) -> list[str]:
        name = str(item.name or "").strip()
        tokens = name.split()
        return _unique_non_empty(
            [
                name,
                " ".join(tokens[:4]),
                " ".join(tokens[:3]),
                " ".join(tokens[:2]),
                tokens[0] if tokens else "",
                str(item.code or "").strip(),
            ]
        )

    def _search_products(self, page: Page, query: str) -> list[dict[str, Any]]:
        search = page.locator(self.sel.item_search_input).first
        search.click()
        search.fill("")
        search.type(query, delay=20)

        with page.expect_response(
            lambda resp: "stores/products/search/similar5" in resp.url and resp.request.method == "POST",
            timeout=self.cfg.runtime.timeout_ms,
        ) as resp_info:
            search.press("Enter")

        response = resp_info.value
        payload = response.json()
        page.wait_for_timeout(500)
        return list(payload.get("data", {}).get("content", []) or [])

    def _find_best_product_match(self, page: Page, item: Item) -> _SearchMatch | None:
        best: _SearchMatch | None = None
        best_key: tuple[float, int, float, int, int, int] | None = None

        for query in self._search_queries_for_item(item):
            results = self._search_products(page, query)
            for idx, result in enumerate(results):
                score = _match_score(item.name or query, result)
                match = _SearchMatch(query=query, row_index=idx, score=score, data=result)
                key = _match_sort_key(item.name or query, result, score)
                if best is None or best_key is None or key > best_key:
                    best = match
                    best_key = key

        if best is None:
            return None
        if not _is_match_acceptable(item.name or best.query, best.data, best.score):
            return None
        return best

    def _open_stores_dialog(self, page: Page, row) -> list[dict[str, Any]]:
        with page.expect_response(
            lambda resp: "stores/products/product/get" in resp.url and resp.request.method == "POST",
            timeout=self.cfg.runtime.timeout_ms,
        ) as resp_info:
            row.locator("button:has-text('Stores')").first.click()

        response = resp_info.value
        page.wait_for_timeout(500)
        payload = response.json()
        stores = list(payload.get("data", []) or [])
        if not stores:
            raise RuntimeError("Stores dialog opened, but no store rows were returned.")
        return stores

    def _choose_store_index(self, stores: list[dict[str, Any]]) -> int:
        mode = str(self.cfg.warehouse_strategy.get("mode", "first_available"))
        if not stores:
            raise RuntimeError("No stores available for selected product.")

        if mode == "first_available":
            for idx, store in enumerate(stores):
                if int(store.get("availableQuantity") or 0) > 0:
                    return idx
            raise _SkipItem("All available stores for this product are out of stock.")

        if mode == "max_available":
            best_idx = 0
            best_qty = -1
            for idx, store in enumerate(stores):
                qty = int(store.get("availableQuantity") or 0)
                if qty > best_qty:
                    best_qty = qty
                    best_idx = idx
            if best_qty <= 0:
                raise _SkipItem("All available stores for this product are out of stock.")
            return best_idx

        raise ValueError(f"Unknown warehouse strategy mode: {mode}")

    def _visible_dialog(self, page: Page):
        dialog = page.locator(".p-dialog:visible").last
        dialog.wait_for(timeout=self.cfg.runtime.timeout_ms)
        return dialog

    def _fill_add_to_cart_dialog(self, page: Page, requested_qty: int) -> None:
        dialog = self._visible_dialog(page)
        dialog.get_by_role("button", name="Add to cart").wait_for(timeout=self.cfg.runtime.timeout_ms)

        qty_input = dialog.locator("input[role='spinbutton']").first
        max_attr = qty_input.get_attribute("aria-valuemax") or qty_input.get_attribute("max") or "1"
        try:
            max_qty = max(1, int(float(max_attr)))
        except Exception:
            max_qty = 1

        qty = max(1, min(int(requested_qty), max_qty))
        qty_input.click()
        qty_input.fill("")
        qty_input.type(str(qty), delay=10)
        page.wait_for_timeout(200)

        dialog.get_by_role("button", name="Add to cart").click()
        page.wait_for_timeout(700)

    def _pick_warehouse_if_needed(self, page: Page) -> None:
        mode = str(self.cfg.warehouse_strategy.get("mode", "first_available"))
        rows = page.locator(self.sel.warehouse_rows)
        if rows.count() == 0:
            return

        if mode == "first_available":
            row = rows.first
            row.locator(self.sel.warehouse_pick_button).first.click()
            page.wait_for_timeout(200)
            return

        if mode == "max_available":
            best_idx = 0
            best_qty = -1
            n = rows.count()
            for i in range(n):
                r = rows.nth(i)
                txt = r.locator(self.sel.warehouse_available_qty).first.inner_text(timeout=1000).strip()
                try:
                    q = int(float(txt.replace(",", "")))
                except Exception:
                    q = 0
                if q > best_qty:
                    best_qty = q
                    best_idx = i
            rows.nth(best_idx).locator(self.sel.warehouse_pick_button).first.click()
            page.wait_for_timeout(200)
            return

        raise ValueError(f"Unknown warehouse strategy mode: {mode}")

    def _confirm_order(self, page: Page) -> None:
        if not self.sel.confirm_order_button:
            return
        # There may be multiple sellers in the cart, each with its own Checkout.
        # Only click enabled ones; otherwise finish without failing.
        checkout = page.locator(self.sel.confirm_order_button)
        enabled = checkout.filter(has_not=page.locator("[disabled]"))
        # `filter(has_not=...)` isn't perfect for all cases; also try a direct CSS for disabled attr.
        enabled_css = page.locator("button:has-text('Checkout'):not([disabled])")

        candidates = enabled_css if enabled_css.count() > 0 else enabled
        n = candidates.count()
        if n == 0:
            print(f"[{self.profile_key}] No enabled Checkout buttons found (cart may be empty, out of stock, or below minimum order).")
            return

        for i in range(n):
            btn = candidates.nth(i)
            try:
                try:
                    btn.click(timeout=5000)
                except Exception:
                    # Dialog overlays may intercept pointer events; retry with force.
                    btn.click(timeout=5000, force=True)
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(500)

                # If a modal dialog appears, try to confirm it.
                dialog = page.locator(".p-dialog:visible")
                if dialog.count() > 0:
                    for label in ("Confirm", "confirm", "Ok", "OK", "Continue", "Yes", "Submit", "تأكيد", "متابعة", "نعم"):
                        c = dialog.locator(f"button:has-text('{label}')")
                        if c.count() > 0:
                            try:
                                c.first.click(timeout=3000)
                                page.wait_for_load_state("networkidle")
                                page.wait_for_timeout(500)
                                break
                            except Exception:
                                pass
            except Exception as e:
                print(f"[{self.profile_key}] Checkout click failed on button {i+1}/{n}: {e}")

