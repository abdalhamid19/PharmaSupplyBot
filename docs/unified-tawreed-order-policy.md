# Unified Tawreed Order Policy

This document describes live Tawreed ordering and the separate Run Results
price-comparison report.

## Live ordering decision

1. Build eligible Tawreed and Excel Target offers for the selected run. Each
   offer must have positive stock, a valid purchase price, and a discount at
   least `min_discount_percent`.
2. Compare Excel Target's lowest persisted purchase price with Tawreed's
   lowest eligible purchase price. If no Tawreed offer meets the discount and
   availability rules but an eligible Excel Target offer exists, defer to Excel
   Target as the only eligible source.
3. Defer the item to Excel Target when:

   ```text
   excel_purchase_price < tawreed_purchase_price + 0.25
   ```

   This includes a lower price, an equal price, and a Tawreed price that is
   less than 0.25 EGP higher. A difference of exactly 0.25 EGP does not defer.
4. If the item remains eligible for Tawreed, exclude out-of-stock offers and
   order by exact purchase price. `preferred_warehouses` breaks exact-price
   ties. The 0.25 EGP tolerance applies to the
   Excel Target gate, not to ordering two Tawreed offers.

## Tawreed allocation modes

The configured order breaks exact-price ties. For this configuration, the
unchanged order in `state/config.yaml` is:

1. شركه البركه (الجيزه)
2. شركه الماسه (مالك سابقا ) (الجيزه)
3. شركه الشفاء ميدكو - الريحان سابقا (الجيزه)
4. شركه الفا فارما (الجيزه)
5. شركه الريان (القاهره)
6. شركه ابو عميره (الجيزه)
7. شركه الادهم (الجيزه)
8. شركه التحرير (الجيزه)

### `lowest_purchase_price` (only supported mode)

The lowest exact purchase price wins. Equal prices use warehouse preference,
then the stable offer identity. The allocator consumes stock from the winning
offer and then repeats the same rule for any remaining quantity.

There are no alternative warehouse modes. The same price-first rule is used for
single-store, multi-store, API, browser, and match-only flows. If a selected
store has only part of the requested quantity, the remaining quantity moves to
the next-lowest-priced store.

The legacy DOM-only warehouse picker exposes stock and row text but no
structured purchase-price field. That fallback cannot apply price ordering;
the price-first rule applies to paths that receive structured Tawreed offers.

## Run Results meanings

- `ordered_qty`: quantity successfully added to the Tawreed basket.
- `added-to-cart`: the Tawreed item had a successful cart addition.
- `deferred-to-excel-target`: Tawreed was intentionally not changed because
  Excel Target won the price rule. Its Tawreed ordered quantity is zero.
- The warehouse winner/comparison panel selects the lowest valid price among
  positive-stock offers that meet the saved `min_discount_percent`, across
  Tawreed and Excel Target. The system uses EGP; differing legacy currency text
  does not exclude an offer. This is price-comparison evidence, not the actual
  basket unless its `ordered_qty` is positive.
- The per-store `is_winner` checkmark applies the same saved discount floor to
  Tawreed and Excel Target offers, so its eligibility rule agrees with the
  price report.

The **Actual Tawreed Basket** section uses only positive `ordered_qty` rows and
is therefore the authoritative store/item view. Partial successful additions
are recorded immediately so a later API/browser failure cannot turn an
unattempted allocation into a reported order.
