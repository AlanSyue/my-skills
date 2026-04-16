#!/usr/bin/env python3
"""Standalone WooCommerce + ECPay reissue script (stdlib only)."""

import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

BASE_URL = "https://flowers.fenny-studio.com"
ECPAY_CREATE_URL = "https://logistics.ecpay.com.tw/Express/Create"
CALLBACK_URL = "https://flowers.fenny-studio.com/wc-api/ry_ecpay_shipping_callback/"
TW_TZ = timezone(timedelta(hours=8))

SHIPPING_SUBTYPE_MAP = {
    "ry_ecpay_shipping_cvs_711": "UNIMARTC2C",
    "ry_ecpay_shipping_cvs_family": "FAMIC2C",
    "ry_ecpay_shipping_cvs_hilife": "HILIFEC2C",
    "ry_ecpay_shipping_cvs_ok": "OKMARTC2C",
}

BLOCKED_STATUSES = {"cancelled", "refunded", "trash", "failed"}


def _try_hex_decode(raw):
    """Detect hex-encoded Keychain output and decode to UTF-8 if appropriate.

    macOS Keychain's ``security -w`` returns hex-encoded bytes for values that
    contain non-ASCII characters (e.g. ``e88aace5a6aee6898be4bd9c`` instead of
    ``芬妮手作``).  Normal ASCII values like merchant IDs or hash keys pass
    through unchanged.
    """
    if not raw or len(raw) % 2 != 0:
        return raw
    if not re.fullmatch(r"[0-9a-f]+", raw):
        return raw
    try:
        decoded = bytes.fromhex(raw).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return raw
    # Only use the decoded value when it actually contains non-ASCII chars;
    # this prevents misinterpreting a hex-looking ASCII value.
    if any(ord(ch) > 127 for ch in decoded):
        return decoded
    return raw


def keychain_get(service):
    """Read a value from macOS Keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", service, "-w"],
            capture_output=True, text=True, check=True,
        )
        raw = result.stdout.strip()
        return _try_hex_decode(raw)
    except subprocess.CalledProcessError:
        print(f"ERROR: {service} not in keychain. Run: /woo-orders setup", file=sys.stderr)
        sys.exit(2)


def load_credentials():
    """Load all credentials from Keychain."""
    return {
        "woo_key": keychain_get("woo-fenny-api-key"),
        "woo_secret": keychain_get("woo-fenny-api-secret"),
        "ecpay_merchant_id": keychain_get("ecpay-merchant-id"),
        "ecpay_hash_key": keychain_get("ecpay-hash-key"),
        "ecpay_hash_iv": keychain_get("ecpay-hash-iv"),
        "ecpay_sender_name": keychain_get("ecpay-sender-name"),
        "ecpay_sender_phone": keychain_get("ecpay-sender-phone"),
        "ecpay_sender_cellphone": keychain_get("ecpay-sender-cellphone"),
    }


def wc_request(method, path, creds, body=None):
    """Make a WooCommerce REST API request."""
    url = f"{BASE_URL}/wp-json/wc/v3{path}"
    auth_str = f"{creds['woo_key']}:{creds['woo_secret']}"
    auth_b64 = __import__("base64").b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "User-Agent": "woo-reissue/1.0",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
        raise RuntimeError(f"WC API {method} {path} HTTP {e.code}: {error_body}")


def compute_check_mac_value(params, hash_key, hash_iv):
    """Compute ECPay CheckMacValue (MD5, .NET-style URL encoding)."""
    sorted_keys = sorted(params.keys())
    parts = [f"{k}={params[k]}" for k in sorted_keys]
    raw = f"HashKey={hash_key}&{'&'.join(parts)}&HashIV={hash_iv}"
    # URL encode: use quote with safe='' then replace %20 with + to match Go's url.QueryEscape
    encoded = urllib.parse.quote(raw, safe="")
    encoded = encoded.replace("%20", "+")
    # Lowercase
    encoded = encoded.lower()
    # .NET-style replacements
    encoded = encoded.replace("%2d", "-")
    encoded = encoded.replace("%5f", "_")
    encoded = encoded.replace("%2e", ".")
    encoded = encoded.replace("%21", "!")
    encoded = encoded.replace("%2a", "*")
    encoded = encoded.replace("%28", "(")
    encoded = encoded.replace("%29", ")")
    # MD5 → uppercase hex
    return hashlib.md5(encoded.encode("utf-8")).hexdigest().upper()


def sanitize_receiver_name(last_name, first_name):
    """Build and sanitize receiver name."""
    name = ((last_name or "") + (first_name or "")).strip()
    if not name:
        return ""
    # Check if pure ASCII
    try:
        name.encode("ascii")
        is_ascii = True
    except UnicodeEncodeError:
        is_ascii = False

    if is_ascii:
        return name[:10]
    else:
        # Strip ASCII letters and digits, keep CJK/symbols
        filtered = "".join(ch for ch in name if not ch.isascii() or (not ch.isalpha() and not ch.isdigit()))
        return filtered[:5]


def regenerate_tracking(order_id, creds):
    """Regenerate ECPay tracking for a single order. Returns a result dict."""
    result = {
        "order_id": order_id,
        "success": False,
        "new_payment_no": "-",
        "logistics_id": "-",
        "sub_type": "",
        "error": "",
    }

    try:
        # a. GET order
        order = wc_request("GET", f"/orders/{order_id}", creds)

        # b. Status gate
        status = order.get("status", "")
        if status in BLOCKED_STATUSES:
            result["error"] = f"訂單狀態為 {status}，不允許重新取號"
            return result

        # c. Shipping method gate
        shipping_lines = order.get("shipping_lines", [])
        if not shipping_lines:
            result["error"] = "訂單沒有運送項目，無法重新取號"
            return result

        method_id = shipping_lines[0].get("method_id", "")
        if not method_id.startswith("ry_ecpay_shipping_cvs_"):
            result["error"] = f"此訂單的運送方式不是綠界超商取貨（目前：{method_id}），無法重新取號"
            return result

        sub_type = SHIPPING_SUBTYPE_MAP.get(method_id)
        if sub_type is None:
            result["error"] = f"不支援的綠界 C2C 子類型：{method_id}"
            return result

        # d. Store ID
        store_id = ""
        for meta in order.get("meta_data", []):
            if meta.get("key") == "_shipping_cvs_store_ID":
                store_id = str(meta.get("value", ""))
                break
        if not store_id:
            result["error"] = "missing _shipping_cvs_store_ID meta"
            return result

        # e. GoodsAmount
        total = order.get("total", "0")
        try:
            goods_amount = round(float(total))
        except (ValueError, TypeError):
            goods_amount = 0
        if goods_amount <= 0:
            result["error"] = f"invalid GoodsAmount from order.Total: {total}"
            return result

        # f. GoodsName
        line_items = order.get("line_items", [])
        if not line_items:
            result["error"] = "order has no line items"
            return result
        goods_name = line_items[0].get("name", "")
        # Truncate to 20 chars (unicode-safe)
        goods_name = goods_name[:20]

        # g. ReceiverName
        shipping = order.get("shipping", {})
        receiver_name = sanitize_receiver_name(
            shipping.get("last_name", ""),
            shipping.get("first_name", ""),
        )
        if not receiver_name:
            result["error"] = "empty receiver name"
            return result

        # h. ReceiverCell
        receiver_cell = (shipping.get("phone", "") or "").replace("-", "").replace(" ", "")
        if not receiver_cell:
            result["error"] = "empty receiver phone"
            return result

        # i. WC write pre-check
        customer_note = order.get("customer_note", "")
        try:
            wc_request("PUT", f"/orders/{order_id}", creds, {"customer_note": customer_note})
        except Exception as e:
            result["error"] = f"WC write permission check failed: {e}"
            return result

        # j. Build ECPay params
        now = datetime.now(TW_TZ)
        ts = str(int(now.timestamp()))
        reversed_ts = ts[::-1]
        rand_digit = str(random.randint(0, 9))
        merchant_trade_no = f"{order_id}TS{rand_digit}{reversed_ts}"
        merchant_trade_date = now.strftime("%Y/%m/%d %H:%M:%S")

        params = {
            "MerchantID": creds["ecpay_merchant_id"],
            "MerchantTradeNo": merchant_trade_no,
            "MerchantTradeDate": merchant_trade_date,
            "LogisticsType": "CVS",
            "LogisticsSubType": sub_type,
            "GoodsAmount": str(goods_amount),
            "GoodsName": goods_name,
            "IsCollection": "N",
            "CollectionAmount": "0",
            "SenderName": creds["ecpay_sender_name"],
            "SenderPhone": creds["ecpay_sender_phone"],
            "SenderCellPhone": creds["ecpay_sender_cellphone"],
            "ReceiverName": receiver_name,
            "ReceiverCellPhone": receiver_cell,
            "ReceiverStoreID": store_id,
            "ServerReplyURL": CALLBACK_URL,
        }

        # k. CheckMacValue
        params["CheckMacValue"] = compute_check_mac_value(params, creds["ecpay_hash_key"], creds["ecpay_hash_iv"])

        # Logging
        print(
            f"[reissue] order={order_id} MerchantTradeNo={merchant_trade_no} "
            f"subType={sub_type} storeID={store_id} goodsAmount={goods_amount}",
            file=sys.stderr,
        )

        # l. POST to ECPay
        post_data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(
            ECPAY_CREATE_URL,
            data=post_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "woo-reissue/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            ecpay_status = resp.status
            ecpay_body = resp.read().decode("utf-8")

        print(f"[reissue] order={order_id} ECPay HTTP={ecpay_status} body={ecpay_body}", file=sys.stderr)

        # m. Parse response
        parts = ecpay_body.split("|", 1)
        if len(parts) != 2:
            result["error"] = f"ECPay unexpected response: {ecpay_body}"
            return result

        resp_status = parts[0].strip()
        resp_kv_str = parts[1].strip()

        if resp_status != "1":
            result["error"] = f"ECPay: {resp_kv_str}"
            return result

        resp_kv = dict(item.split("=", 1) for item in resp_kv_str.split("&") if "=" in item)
        logistics_id = resp_kv.get("AllPayLogisticsID", "")
        payment_no = resp_kv.get("CVSPaymentNo", "")
        validation_no = resp_kv.get("CVSValidationNo", "")
        booking_note = resp_kv.get("BookingNote", "")
        if resp_kv.get("LogisticsSubType"):
            sub_type = resp_kv["LogisticsSubType"]

        # n. Merge _ecpay_shipping_info
        existing_info = {}
        for meta in order.get("meta_data", []):
            if meta.get("key") == "_ecpay_shipping_info":
                val = meta.get("value")
                if isinstance(val, dict):
                    existing_info = val
                break

        now_iso = now.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        existing_info[logistics_id] = {
            "ID": logistics_id,
            "LogisticsType": "CVS",
            "LogisticsSubType": sub_type,
            "PaymentNo": payment_no,
            "ValidationNo": validation_no,
            "store_ID": store_id,
            "BookingNote": booking_note,
            "status": 300,
            "status_msg": "已成功",
            "create": now_iso,
            "edit": now_iso,
            "amount": goods_amount,
            "IsCollection": "N",
            "temp": "1",
        }

        # o. PUT meta back
        tracking_number = payment_no + validation_no
        wc_request("PUT", f"/orders/{order_id}", creds, {
            "meta_data": [
                {"key": "_ecpay_shipping_info", "value": existing_info},
                {"key": "運送編號", "value": tracking_number},
            ]
        })

        # p. Collect result
        result["success"] = True
        result["new_payment_no"] = tracking_number
        result["logistics_id"] = logistics_id
        result["sub_type"] = sub_type

    except Exception as e:
        result["error"] = str(e)

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: woo_orders_reissue.py <order_id> [<order_id>...]", file=sys.stderr)
        sys.exit(1)

    order_ids = []
    for arg in sys.argv[1:]:
        try:
            order_ids.append(int(arg))
        except ValueError:
            print(f"ERROR: invalid order ID: {arg}", file=sys.stderr)
            sys.exit(1)

    creds = load_credentials()
    results = [regenerate_tracking(oid, creds) for oid in order_ids]

    ok = sum(1 for r in results if r["success"])
    fail = len(results) - ok
    print(f"共 {len(results)} 筆（成功 {ok} / 失敗 {fail}）")
    print()
    print("| 訂單 | 結果 | 新運送編號 | LogisticsID | 備註 |")
    print("|---|---|---|---|---|")
    for r in results:
        status = "✓" if r["success"] else "✗"
        err = r.get("error") or "-"
        print(f"| {r['order_id']} | {status} | {r['new_payment_no']} | {r['logistics_id']} | {err} |")


if __name__ == "__main__":
    main()
