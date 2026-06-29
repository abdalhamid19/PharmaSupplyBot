# خطة إصلاح API add_to_cart الجذرية

**الهدف:** إصلاح API add_to_cart لتعمل بشكل صحيح بدون الحاجة لـ browser fallback

**التاريخ:** 2026-06-23  
**الحالة:** 🔄 مخطط (لم يُنفذ بعد)

---

## المرحلة 1: اكتشاف الـ Payload الصحيح (Critical)

### الخطوة 1.1: تفعيل Browser Network Capture
**الهدف:** التقاط POST request الفعلي من Tawreed website

**الإجراءات:**
```python
# في tawreed_api_discovery.py
def begin_detailed_api_capture(page) -> list[dict[str, Any]]:
    """Capture full request details including headers and payload."""
    captured: list[dict[str, Any]] = []
    
    def capture_handler(request):
        if request.method == "POST" and "cart" in request.url.lower():
            captured.append({
                "url": request.url,
                "method": request.method,
                "headers": dict(request.headers),
                "body": request.post_data_json,
                "timestamp": time.time()
            })
    
    page.on("request", capture_handler)
    return captured
```

**التنفيذ:**
1. تشغيل browser mode مع debug
2. إضافة صنف واحد يدوياً من الموقع
3. حفظ الـ captured request في ملف JSON
4. تحليل الـ payload structure

**المخرجات المتوقعة:**
```json
{
  "url": "https://api.tawreed.io/rest/v2/shopping/carts/items",
  "body": {
    "mode": "...",
    "langCode": "ar",
    "data": {
      "productId": 71904,
      "quantity": 1,
      "storesList": [
        {
          "storeProductId": 2066374,
          "additionalField1": "...",
          "additionalField2": "..."
        }
      ]
    }
  }
}
```

---

## المرحلة 2: تحليل الـ Payload Structure

### الخطوة 2.1: مقارنة Payloads
**الهدف:** فهم الفرق بين الـ payload المُرسل والـ payload الصحيح

**الأدوات:**
```python
# أداة مساعدة للمقارنة
def compare_payloads(captured: dict, current: dict) -> dict:
    """Compare two payloads and highlight differences."""
    differences = {
        "missing_fields": [],
        "extra_fields": [],
        "type_mismatches": [],
        "value_differences": []
    }
    
    # تحليل الفروقات
    captured_data = captured.get("data", {})
    current_data = current.get("data", {})
    
    for key in captured_data:
        if key not in current_data:
            differences["missing_fields"].append(key)
        elif type(captured_data[key]) != type(current_data.get(key)):
            differences["type_mismatches"].append({
                "field": key,
                "expected": type(captured_data[key]).__name__,
                "actual": type(current_data.get(key)).__name__
            })
    
    return differences
```

### الخطوة 2.2: توثيق الـ Payload Schema
**الهدف:** إنشاء schema واضح للـ payload الصحيح

```python
# في tawreed_api_schema.py (ملف جديد)
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class StoreItem:
    """Structure for one store item in storesList."""
    storeProductId: int
    # المزيد من الحقول بعد الاكتشاف

@dataclass
class AddToCartData:
    """Validated structure for add-to-cart data payload."""
    productId: int
    quantity: int
    storesList: List[StoreItem]
    # المزيد من الحقول بعد الاكتشاف

@dataclass
class AddToCartPayload:
    """Complete add-to-cart API payload."""
    mode: str
    langCode: str
    data: AddToCartData
```

---

## المرحلة 3: إصلاح Payload Builder

### الخطوة 3.1: تحديث body_with_match()
**الهدف:** بناء payload صحيح 100% بناءً على المُكتشف

```python
# في tawreed_api_payloads.py
def body_with_match(body: dict[str, Any], match: Any, quantity: int) -> dict[str, Any]:
    """Build correct add-to-cart payload based on discovered schema."""
    payload = _copy_body(body)
    candidate = getattr(match, "data", {}) or {}
    
    store_product_id = candidate_store_product_id(candidate)
    product_id = candidate.get("productId")
    
    # بناء payload حسب الـ schema المُكتشف
    payload["data"] = {
        "productId": product_id,
        "quantity": int(quantity),
        "storesList": [
            _build_store_item(candidate, store_product_id)
        ]
    }
    
    return payload


def _build_store_item(candidate: dict, store_product_id: str) -> dict:
    """Build one storesList item with all required fields."""
    return {
        "storeProductId": int(store_product_id),
        # إضافة الحقول المُكتشفة من المرحلة 1
    }
```

---

## المرحلة 4: التحقق من Authentication

### الخطوة 4.1: فحص Token Validity
**الهدف:** التأكد من أن الـ token صالح وله الصلاحيات المطلوبة

```python
# في tawreed_api_auth.py (ملف جديد)
def validate_cart_permissions(state_path: Path) -> tuple[bool, str]:
    """Verify token has cart modification permissions."""
    token = access_token_from_state(state_path)
    
    if not token:
        return False, "No token found"
    
    if is_token_expired(state_path):
        return False, "Token expired"
    
    # فك تشفير JWT payload
    payload = _jwt_payload(token)
    permissions = payload.get("permissions", [])
    
    if "cart:write" not in permissions:
        return False, "Token missing cart:write permission"
    
    return True, "Token valid"
```

### الخطوة 4.2: فحص Headers
**الهدف:** التأكد من إرسال كل الـ headers المطلوبة

```python
# في tawreed_api.py
def _ensure_request_context(self):
    """Create request context with all required headers."""
    if self._request_context is None:
        self._playwright = sync_playwright().start()
        
        # جمع كل الـ headers من browser state
        headers = {
            **_auth_headers_from_state(self.state_path),
            **_required_tawreed_headers()
        }
        
        self._request_context = self._playwright.request.new_context(
            storage_state=str(self.state_path),
            base_url=_api_origin(self.base_url),
            extra_http_headers=headers,
        )
    return self._request_context


def _required_tawreed_headers() -> dict[str, str]:
    """Return headers required by Tawreed API."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Origin": "https://seller.tawreed.io",
        "Referer": "https://seller.tawreed.io/",
        # المزيد بعد الاكتشاف من browser
    }
```

---

## المرحلة 5: تحديث API Contract Discovery

### الخطوة 5.1: Enhanced Contract Capture
**الهدف:** التقاط payload structure الكامل وليس فقط URL

```python
# في tawreed_api_contract.py
@dataclass(frozen=True)
class TawreedApiContract:
    """Enhanced API contract with full payload structure."""
    
    product_search_url: str = ""
    product_search_body: dict[str, Any] | None = None
    
    add_to_cart_url: str = ""
    add_to_cart_body_template: dict[str, Any] | None = None
    add_to_cart_required_fields: list[str] | None = None
    add_to_cart_example_payload: dict[str, Any] | None = None
    
    # المزيد من الحقول


def save_enhanced_contract(
    captured_requests: list[dict[str, Any]], 
    path: Path = DEFAULT_CONTRACT_PATH
) -> TawreedApiContract:
    """Save contract with full payload examples."""
    
    # البحث عن add-to-cart request
    add_to_cart_req = _find_add_to_cart_request(captured_requests)
    
    if add_to_cart_req:
        contract = TawreedApiContract(
            add_to_cart_url=add_to_cart_req["url"],
            add_to_cart_body_template=_extract_template(add_to_cart_req["body"]),
            add_to_cart_required_fields=_extract_required_fields(add_to_cart_req["body"]),
            add_to_cart_example_payload=add_to_cart_req["body"]
        )
    
    # حفظ كـ JSON مع التفاصيل الكاملة
    _save_contract_json(contract, path)
    
    return contract
```

---

## المرحلة 6: إضافة Validation Layer

### الخطوة 6.1: Payload Validation
**الهدف:** التحقق من صحة الـ payload قبل الإرسال

```python
# في tawreed_api_validation.py (ملف جديد)
class PayloadValidationError(Exception):
    """Raised when payload validation fails."""
    pass


def validate_add_to_cart_payload(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate payload against discovered schema."""
    errors = []
    
    # فحص الحقول المطلوبة
    data = payload.get("data", {})
    
    if not data.get("productId"):
        errors.append("Missing productId")
    
    if not data.get("quantity") or data.get("quantity") <= 0:
        errors.append("Invalid quantity")
    
    stores_list = data.get("storesList", [])
    if not stores_list or not isinstance(stores_list, list):
        errors.append("Invalid or missing storesList")
    else:
        for idx, store in enumerate(stores_list):
            if not store.get("storeProductId"):
                errors.append(f"Missing storeProductId in storesList[{idx}]")
    
    return len(errors) == 0, errors


# استخدام في TawreedApiClient
def add_to_cart(self, match: Any, quantity: int) -> None:
    """Add item with payload validation."""
    if not self.contract.add_to_cart_url:
        raise TawreedApiUnavailable("No add-to-cart contract.")
    
    payload = body_with_match(self.contract.add_to_cart_body or {}, match, quantity)
    
    # Validate قبل الإرسال
    valid, errors = validate_add_to_cart_payload(payload)
    if not valid:
        raise PayloadValidationError(f"Invalid payload: {', '.join(errors)}")
    
    self._post_json(self.contract.add_to_cart_url, payload)
```

---

## المرحلة 7: إضافة Detailed Logging

### الخطوة 7.1: Request/Response Logging
**الهدف:** تسجيل كل التفاصيل لـ debugging

```python
# في tawreed_api.py
def _post_json(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
    """POST with detailed logging."""
    import logging
    logger = logging.getLogger("tawreed.api")
    
    # Log request
    logger.debug(f"API Request: POST {url}")
    logger.debug(f"API Payload: {json.dumps(body, indent=2, ensure_ascii=False)}")
    
    response = self._ensure_request_context().post(url, data=body, timeout=60_000)
    
    # Log response
    logger.debug(f"API Response Status: {response.status}")
    logger.debug(f"API Response Headers: {dict(response.headers)}")
    
    if not response.ok:
        logger.error(f"API Error: {response.status} {response.status_text}")
        logger.error(f"Response Body: {response.text()}")
        raise TawreedApiUnavailable(
            f"Tawreed API returned HTTP {response.status}: {response.status_text}"
        )
    
    payload = response.json()
    logger.debug(f"API Response Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    # Check for error in payload
    if isinstance(payload, dict):
        status = payload.get("status")
        if status and status >= 400:
            logger.error(f"API Payload Error: {payload}")
            raise TawreedApiUnavailable(
                f"Tawreed API error {status}: {payload.get('message', 'Unknown error')}"
            )
    
    return payload if isinstance(payload, dict) else {"data": payload}
```

---

## المرحلة 8: Testing Strategy

### الخطوة 8.1: Unit Tests لـ Payload Builder
```python
# في tests/test_tawreed_api_payloads.py
def test_body_with_match_structure():
    """Test payload has correct structure."""
    match = Mock(data={
        "productId": 12345,
        "storeProductId": 67890,
        "productName": "Test Product"
    })
    
    body = {"mode": "error", "langCode": "ar", "data": {}}
    result = body_with_match(body, match, 5)
    
    assert result["data"]["productId"] == 12345
    assert result["data"]["quantity"] == 5
    assert isinstance(result["data"]["storesList"], list)
    assert len(result["data"]["storesList"]) == 1
    assert result["data"]["storesList"][0]["storeProductId"] == 67890


def test_body_with_match_validates_required_fields():
    """Test validation catches missing fields."""
    match = Mock(data={"productId": None})
    
    body = {"mode": "error", "langCode": "ar", "data": {}}
    
    with pytest.raises(ValueError):
        body_with_match(body, match, 1)
```

### الخطوة 8.2: Integration Test مع API الحقيقي
```python
# في tests/test_tawreed_api_integration.py
@pytest.mark.integration
def test_add_to_cart_api_success(valid_state_path):
    """Test successful add to cart via API."""
    with TawreedApiClient("https://seller.tawreed.io", valid_state_path) as api:
        # بحث عن منتج حقيقي
        products = api.search_products("Panadol")
        assert len(products) > 0
        
        match = Mock(data=products[0])
        
        # محاولة الإضافة
        api.add_to_cart(match, 1)
        
        # التحقق من السلة (يحتاج API endpoint للقراءة)
        # cart_items = api.get_cart_items()
        # assert any(item["productId"] == products[0]["productId"] for item in cart_items)
```

---

## المرحلة 9: Rollout Plan

### الخطوة 9.1: تفعيل تدريجي
```python
# في config.yaml
api:
  add_to_cart:
    enabled: true
    validation_mode: "strict"  # strict, lenient, disabled
    fallback_on_error: true
    log_level: "debug"
```

### الخطوة 9.2: A/B Testing
```python
# اختبار API الجديد مع نسبة من الأصناف
def should_use_new_api() -> bool:
    """Gradually roll out new API."""
    import random
    rollout_percentage = 10  # ابدأ بـ 10%
    return random.random() < (rollout_percentage / 100)


def place_order_with_api(bot, items):
    """Place order with gradual API rollout."""
    if should_use_new_api():
        try:
            _place_order_with_new_api(bot, items)
        except Exception as e:
            logger.warning(f"New API failed, falling back: {e}")
            _place_order_with_browser(bot, items)
    else:
        _place_order_with_browser(bot, items)
```

---

## المرحلة 10: Monitoring & Metrics

### الخطوة 10.1: إضافة Metrics
```python
# في tawreed_api_metrics.py (ملف جديد)
class ApiMetrics:
    """Track API performance and success rates."""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.fallback_count = 0
        self.avg_response_time = 0.0
    
    def record_success(self, response_time: float):
        self.total_requests += 1
        self.successful_requests += 1
        self._update_avg_response_time(response_time)
    
    def record_failure(self, error_type: str):
        self.total_requests += 1
        self.failed_requests += 1
    
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def report(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "success_rate": self.success_rate(),
            "avg_response_time_ms": self.avg_response_time * 1000,
            "fallback_rate": self.fallback_count / max(self.total_requests, 1)
        }
```

---

## الجدول الزمني المقترح

| المرحلة | المدة المقدرة | الأولوية |
|---------|---------------|----------|
| 1. Network Capture | 2 ساعات | 🔴 Critical |
| 2. Payload Analysis | 1 ساعة | 🔴 Critical |
| 3. Fix Payload Builder | 2 ساعات | 🔴 Critical |
| 4. Auth Verification | 1 ساعة | 🟡 High |
| 5. Contract Update | 2 ساعات | 🟡 High |
| 6. Validation Layer | 2 ساعات | 🟢 Medium |
| 7. Logging | 1 ساعة | 🟢 Medium |
| 8. Testing | 3 ساعات | 🔴 Critical |
| 9. Rollout | 1 ساعة | 🟡 High |
| 10. Monitoring | 1 ساعة | 🟢 Medium |

**إجمالي:** ~16 ساعة عمل

---

## المخاطر والتحديات

### المخاطر المحتملة
1. **Payload structure معقد** - قد يحتوي على حقول خفية أو ديناميكية
2. **API قد تتغير** - Tawreed قد تغير API بدون إشعار
3. **CSRF tokens** - قد يكون هناك tokens ديناميكية مطلوبة
4. **Rate limiting** - API قد تحد من عدد الطلبات

### استراتيجيات التخفيف
1. **Network capture شامل** - التقاط عدة requests للتأكد من consistency
2. **Contract versioning** - تتبع versions والتحقق منها
3. **Token refresh** - refresh تلقائي عند الحاجة
4. **Retry logic** - إعادة محاولة ذكية مع backoff

---

## معايير النجاح

✅ **المعيار 1:** API add_to_cart تنجح 95%+ من الوقت  
✅ **المعيار 2:** لا حاجة لـ browser fallback في الحالات العادية  
✅ **المعيار 3:** Response time < 1 ثانية للإضافة  
✅ **المعيار 4:** الأصناف تظهر في السلة فوراً  
✅ **المعيار 5:** لا regression في functionality أخرى  

---

## الخطوات التالية (Next Actions)

1. ✅ **الموافقة على الخطة** من المستخدم
2. 🔄 **تنفيذ المرحلة 1** - Network capture
3. 🔄 **تحليل النتائج** وتحديد الـ payload الصحيح
4. 🔄 **تطبيق الإصلاح** في الكود
5. 🔄 **الاختبار الشامل**
6. 🔄 **التفعيل التدريجي**

---

**ملاحظة مهمة:** هذه الخطة تتطلب الوصول إلى browser capture حقيقي لاكتشاف الـ payload الصحيح. بدون ذلك، سنظل نخمن الـ structure.
