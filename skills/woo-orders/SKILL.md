---
name: woo-orders
description: >-
  Query and manage WooCommerce orders on flowers.fenny-studio.com.
  (1) Look up orders by product ID or Chinese keyword — e.g. "哪些訂單買了鬱金香材料包"、"4182 被誰訂了"、"查一下 DIY 材料包的訂單".
  (2) Look up orders by shipping tracking number (運送編號) — e.g. "P93479717606 是哪張單"、"查物流單 R53049771167".
  (3) Filter orders by 希望送達時間 (desired delivery date) — e.g. "明天要出哪些貨"、"4/15 要送的訂單"、"本週出貨清單".
  (4) Reissue ECPay C2C tracking number for expired logistics — e.g. "4372 重打綠界"、"物流單過期了重新產生"、"reissue tracking".
  (5) Query ECPay logistics status — e.g. "誰到店了"、"查物流狀態"、"列到店待取的訂單"、"已寄出的訂單目前狀況"、"4345 現在物流狀態".
---

# WooCommerce 訂單查詢 (flowers.fenny-studio.com)

## 這個 skill 做什麼
查詢 `flowers.fenny-studio.com` 上的訂單，支援多種查法：
- 以產品 ID 或中文關鍵字查「哪些訂單買了該商品」
- `track`：以運送編號（meta key `運送編號`）查訂單
- `deliver`：以希望送達時間（meta key `希望送達時間`）列出訂單
- `logistics`：以物流狀態（`_ecpay_shipping_info` + WC 狀態）列訂單
- `reissue`：對指定訂單重新呼叫綠界 Create API 取得新的 7-11 C2C 運送編號（非 read-only，會寫回 WooCommerce 訂單 meta）

輸出訂單 ID、狀態、日期、相關 meta 欄位、以及 WordPress 後台編輯連結。

Read-only：不做任何寫入、退款或狀態轉換。

## 憑證來源
- `WOO_API_KEY` / `WOO_API_SECRET` **只**從 macOS Keychain 讀取
- ECPay 憑證（`reissue` 子命令使用）也**只**從 macOS Keychain 讀取
- 絕對不要 fallback 去讀 `~/simple-checklist/.env` 或其他 `.env`
- Keychain item：
  - service=`woo-fenny-api-key`, account=`$USER` → consumer key
  - service=`woo-fenny-api-secret`, account=`$USER` → consumer secret
  - service=`ecpay-merchant-id`, account=`$USER` → ECPay 特店代號
  - service=`ecpay-hash-key`, account=`$USER` → ECPay HashKey
  - service=`ecpay-hash-iv`, account=`$USER` → ECPay HashIV
  - service=`ecpay-sender-name`, account=`$USER` → 寄件人姓名
  - service=`ecpay-sender-phone`, account=`$USER` → 寄件人電話
  - service=`ecpay-sender-cellphone`, account=`$USER` → 寄件人手機

## 參數 parsing 規則
看第一個參數決定走哪條路：

| 使用者輸入 | 行為 |
|---|---|
| `track <運送編號> [--all]` | 用 `woo_orders_track.sh` 查運送編號 |
| `deliver [<日期> [<日期>]] [--all]` | 用 `woo_orders_deliver.sh` 查希望送達時間 |
| `logistics [<keyword>] [--all]` | 用 `woo_orders_logistics.sh` 查物流狀態 |
| `reissue <訂單ID> [<訂單ID>...]` | 用 `woo_orders_reissue.sh` 重打綠界取號 |
| 純數字 (e.g. `4182`) | 直接以產品 ID 查訂單 |
| `setup` | 進入一次性憑證設定流程（見下方 Setup） |
| `setup --reset` | 同上，覆寫既有 keychain item |
| 其他字串 (e.g. `鬱金香`) | 先搜尋產品，唯一命中直接查；多重命中列出讓使用者挑 |
| 無參數 / `--help` | 顯示 usage |

## 執行腳本

主腳本：
```bash
bash "$HOME/my-skills/scripts/woo_orders_by_product.sh" <arg>
```

該腳本會自動 `source` `$HOME/my-skills/scripts/woo_keychain.sh` 載入 keychain 憑證。

### 產品 ID 路徑
直接把 ID 丟進去即可，範例：
```bash
bash "$HOME/my-skills/scripts/woo_orders_by_product.sh" 4182
```

輸出格式：
```
產品：鬱金香 DIY 材料包 (4182)
共 3 筆訂單（status=any）：

| 訂單 ID | 狀態 | 日期 | 物流狀態 | 更新 | 後台連結 |
|---|---|---|---|---|---|
| 4372 | 處理中 | 2026-04-09 | (未寄出) | - | https://flowers.fenny-studio.com/wp-admin/post.php?post=4372&action=edit |
| 4316 | 已完成 | 2026-03-24 | 買家已到店取貨 | 2026-03-28 | https://flowers.fenny-studio.com/wp-admin/post.php?post=4316&action=edit |
| 4311 | 已完成 | 2026-03-23 | 買家已到店取貨 | 2026-03-27 | https://flowers.fenny-studio.com/wp-admin/post.php?post=4311&action=edit |
```

`物流狀態` / `更新` 來自 `_ecpay_shipping_info` 最新條目的 `status_msg` / `edit`（見下方 `logistics` 子命令說明）；WC 狀態不在 post-ship 範圍（已出貨/到店待取/已離店/已完成）時固定顯示 `(未寄出)`。

### 關鍵字路徑
```bash
bash "$HOME/my-skills/scripts/woo_orders_by_product.sh" 鬱金香
```

**多重命中時**：腳本會列出所有候選產品 ID + 名稱並 exit 0。此時 **不要自作主張挑一個**，把清單原樣呈現給使用者，請使用者回覆指定 ID，再用純 ID 模式跑一次。

**唯一命中時**：自動查該產品的訂單，輸出與產品 ID 路徑相同格式。

**沒有命中時**：腳本會印 `沒有產品匹配「<keyword>」` 並 exit 1。

## `track` 子命令 — 以運送編號查訂單

```bash
bash "$HOME/my-skills/scripts/woo_orders_track.sh" <tracking_number>
bash "$HOME/my-skills/scripts/woo_orders_track.sh" <tracking_number> --all
```

規則：
- **完全相符**（exact match），不做 substring / fuzzy
- 預設 scope：`status=processing`
- 加 `--all` 才會掃全部狀態（`status=any`）
- 若預設 scope 沒找到，訊息會提示「加 --all 可掃全部狀態」
- 通常是唯一命中，但若多筆命中也會一併列出

輸出範例：
```
找到 1 筆訂單（運送編號 === P93479717606，scope: all statuses）：

| 訂單 ID | 狀態 | 下單日 | 物流狀態 | 更新 | 運送編號 | 後台連結 |
|---|---|---|---|---|---|---|
| 4316 | 已完成 | 2026-03-24 | 買家已到店取貨 | 2026-03-28 | P93479717606 | https://flowers.fenny-studio.com/wp-admin/post.php?post=4316&action=edit |
```

## `deliver` 子命令 — 以希望送達時間列訂單

```bash
# 所有已填寫希望送達時間的訂單
bash "$HOME/my-skills/scripts/woo_orders_deliver.sh"

# 單日 exact match
bash "$HOME/my-skills/scripts/woo_orders_deliver.sh" 2026-04-15

# 日期區間 [start, end] 包含兩端
bash "$HOME/my-skills/scripts/woo_orders_deliver.sh" 2026-04-08 2026-04-18

# 掃全部狀態
bash "$HOME/my-skills/scripts/woo_orders_deliver.sh" 2026-04-15 --all
```

規則：
- 預設 scope：`status=processing`；加 `--all` 掃全部狀態
- **一律排除 `希望送達時間 == '未填寫'`** 的訂單
- 單日：`hope == <date>`
- 區間：`start <= hope <= end`（字串字典序比較，因格式固定為 `YYYY-MM-DD`）
- 無參數：只要 `希望送達時間` 非 `未填寫` 都列出
- 結果依 `希望送達時間` 升冪排序，同日期再依訂單 ID 升冪
- `運送編號` 為空時顯示 `(未出貨)` 讓欄位對齊

輸出範例：
```
希望送達時間 = 2026-04-15，共 1 筆訂單（scope: processing）：

| 訂單 ID | 狀態 | 希望送達 | 物流狀態 | 更新 | 運送編號 | 後台連結 |
|---|---|---|---|---|---|---|
| 4372 | 處理中 | 2026-04-15 | (未寄出) | - | (未出貨) | https://flowers.fenny-studio.com/wp-admin/post.php?post=4372&action=edit |
```

## `logistics` 子命令 — 以物流狀態列訂單

```bash
# 預設：已寄出 + 到店待取 + 已離店（不含已完成）
bash "$HOME/my-skills/scripts/woo_orders_logistics.sh"

# 只看到店待取
bash "$HOME/my-skills/scripts/woo_orders_logistics.sh" at-cvs

# 只看已離店（剛離開門市，往使用者方向）
bash "$HOME/my-skills/scripts/woo_orders_logistics.sh" out-cvs

# 只看剛寄出、還沒進門市
bash "$HOME/my-skills/scripts/woo_orders_logistics.sh" sent

# 只看已完成
bash "$HOME/my-skills/scripts/woo_orders_logistics.sh" completed

# 包含 completed 的全部 post-ship
bash "$HOME/my-skills/scripts/woo_orders_logistics.sh" --all
```

Keyword → WC status 對應：

| keyword | WC status | 中文 |
|---|---|---|
| `(省略)` | `already-sent,ry-at-cvs,ry-out-cvs` | 已寄出 / 到店待取 / 已離店 |
| `at-cvs` | `ry-at-cvs` | 到店待取 |
| `out-cvs` | `ry-out-cvs` | 已離店 |
| `sent` | `already-sent` | 已寄出 |
| `completed` | `completed` | 已完成 |
| `--all` | `already-sent,ry-at-cvs,ry-out-cvs,completed` | 全部 post-ship（含已完成） |

規則：
- **預設不含 `completed` 與 `processing`**，目的是讓值班只看「目前還在物流鏈上、需要盯」的訂單
- 結果依每筆訂單 `_ecpay_shipping_info` 當前條目的 `edit` 時間 **DESC 排序**（最新事件在最上面）
- 沒有 `edit` 或沒抓到 `_ecpay_shipping_info` 的訂單排在最後（以 order ID desc 當 tiebreaker）
- 資料來源：
  - `物流狀態` = `_ecpay_shipping_info[<id>].status_msg`
  - `更新` = `_ecpay_shipping_info[<id>].edit[:10]`
  - 挑選哪個 `<id>`：先找 `PaymentNo + ValidationNo == 運送編號`，否則取 LogisticsID 最大的那筆
- 若訂單沒有任何 `_ecpay_shipping_info`（理論上 post-ship 不會發生），物流狀態顯示 `(無資料)`
- Read-only：不寫任何 meta、不碰綠界 API

輸出範例：
```
查詢範圍：已寄出 / 到店待取 / 已離店，共 2 筆：

| 訂單 ID | WC 狀態 | 物流狀態 | 更新 | 運送編號 | 後台連結 |
|---|---|---|---|---|---|
| 4372 | 到店待取 | 商品已送達門市 | 2026-04-11 | X12345677890 | https://flowers.fenny-studio.com/wp-admin/post.php?post=4372&action=edit |
| 4369 | 已出貨 | 已成功 | 2026-04-10 | P93479717700 | https://flowers.fenny-studio.com/wp-admin/post.php?post=4369&action=edit |
```

0 筆時：
```
查詢範圍：到店待取，共 0 筆訂單
```

## `reissue` 子命令 — 重新呼叫綠界 Create API 取號

當 7-11 C2C 運送編號過期（約 7 天）時，用這個子命令批次重打綠界正式環境，取得新的 `CVSPaymentNo + CVSValidationNo` 並寫回 WooCommerce 訂單的 `_ecpay_shipping_info` 與 `運送編號` meta。

```bash
bash "$HOME/my-skills/scripts/woo_orders_reissue.sh" <訂單ID> [<訂單ID>...]
```

範例：
```bash
# 單筆重打
bash "$HOME/my-skills/scripts/woo_orders_reissue.sh" 4372

# 批次重打兩筆（例：/woo-orders reissue 4372 4383）
bash "$HOME/my-skills/scripts/woo_orders_reissue.sh" 4372 4383
```

規則：
- **非 read-only**：會打綠界正式環境 `https://logistics.ecpay.com.tw/Express/Create`，並 PUT 回 WooCommerce 訂單 meta。執行前不會再問確認，呼叫下去直接打綠界正式環境。
- 腳本直接呼叫 WooCommerce REST API 與綠界 Logistics API，不依賴任何 backend 服務。
- 憑證來源：macOS Keychain（WooCommerce + ECPay，共 8 個 item，見上方「憑證來源」）。
- 每筆獨立回報：逐筆處理，失敗的訂單不會中斷整批。
- 若訂單既沒有現有的 `_ecpay_shipping_info`，也沒辦法從 `shipping_lines[0].method_id` 推出 `LogisticsSubType`（只支援 `ry_ecpay_shipping_cvs_{711,family,hilife,ok}`），腳本會回報對應錯誤訊息。

輸出範例：
```
共 2 筆（成功 1 / 失敗 1）

| 訂單 | 結果 | 新運送編號 | LogisticsID | 備註 |
|---|---|---|---|---|
| 4372 | ✓ | X12345677890 | 48102394 | - |
| 4383 | ✗ | - | - | ECPay: 訂單已存在 |
```

失敗的訂單會在 `備註` 欄位顯示綠界回傳的原始錯誤訊息（或 backend 的前置檢查錯誤，例如 `missing _shipping_cvs_store_ID meta`）。

## 錯誤處理

### Keychain 沒有憑證
腳本（透過 `woo_keychain.sh`）會以 exit code 2 離開，並印：
```
ERROR: woo-fenny-api-key not in keychain. Run: /woo-orders setup
```
或
```
ERROR: woo-fenny-api-secret not in keychain. Run: /woo-orders setup
```

看到這個錯誤時：
1. **只**告訴使用者請跑 `/woo-orders setup`
2. **不**要嘗試去讀 `~/simple-checklist/.env`、`~/my-skills/.env` 或任何其他檔案當 fallback
3. **不**要自己去 `security find-generic-password` 或用其他方式繞過

### Keychain 授權彈窗
macOS 第一次執行（或憑證剛寫入後的第一次讀取）時，會彈出 Keychain 授權對話框問是否允許這個程式讀取該 item。請使用者點 **「一律允許 / Always Allow」**，後續呼叫（包括 bot context）才能靜默執行。

## Setup 子命令

當使用者下 `/woo-orders setup` 時：

1. 在對話中向使用者詢問以下憑證（例如用 AskUserQuestion 或直接請他貼）。**不要**從任何 `.env` 檔讀取當預設值。
   - WooCommerce：consumer key、consumer secret
   - ECPay：merchant ID、hash key、hash IV、寄件人姓名、寄件人電話、寄件人手機
2. 拿到值之後，用 Bash 執行：
   ```bash
   # WooCommerce
   security add-generic-password -U -a "$USER" -s woo-fenny-api-key    -w '<KEY>'
   security add-generic-password -U -a "$USER" -s woo-fenny-api-secret -w '<SECRET>'
   # ECPay
   security add-generic-password -U -a "$USER" -s ecpay-merchant-id      -w '<MERCHANT_ID>'
   security add-generic-password -U -a "$USER" -s ecpay-hash-key         -w '<HASH_KEY>'
   security add-generic-password -U -a "$USER" -s ecpay-hash-iv          -w '<HASH_IV>'
   security add-generic-password -U -a "$USER" -s ecpay-sender-name      -w '<SENDER_NAME>'
   security add-generic-password -U -a "$USER" -s ecpay-sender-phone     -w '<SENDER_PHONE>'
   security add-generic-password -U -a "$USER" -s ecpay-sender-cellphone -w '<SENDER_CELLPHONE>'
   ```
   `-U` 允許覆寫既有 item，`setup --reset` 也是走同一行（指令本身冪等）。
3. 驗證可以讀出來並打通 API：
   ```bash
   source "$HOME/my-skills/scripts/woo_keychain.sh" \
     && curl -sf -u "$WOO_API_KEY:$WOO_API_SECRET" \
        "$WOO_BASE_URL/wp-json/wc/v3/products?per_page=1" >/dev/null \
     && echo OK
   ```
4. 提醒使用者：下一次真正跑查詢時，macOS 會彈 Keychain 授權視窗，請點「一律允許」，之後 bot 呼叫就能靜默執行。

## Examples
```
/woo-orders 4182
/woo-orders 鬱金香
/woo-orders 瑪格麗特
/woo-orders track P93479717606
/woo-orders track P93479717606 --all
/woo-orders deliver
/woo-orders deliver 2026-04-15
/woo-orders deliver 2026-04-08 2026-04-18
/woo-orders deliver 2026-04-15 --all
/woo-orders logistics
/woo-orders logistics at-cvs
/woo-orders logistics sent
/woo-orders logistics --all
/woo-orders reissue 4372
/woo-orders reissue 4372 4383
/woo-orders setup
/woo-orders setup --reset
```

## Constraints
- 大部分子命令（`track` / `deliver` / `logistics` / 產品 ID / 關鍵字）為 read-only，不做訂單寫入、狀態轉換、退款
- `reissue` 是例外：直接呼叫綠界正式環境 Create API，並寫回 WooCommerce 訂單的 `_ecpay_shipping_info` 與 `運送編號` meta
- Base URL 寫死為 `https://flowers.fenny-studio.com`，不支援多店
- 不遷移、不修改其他 skill 的 `.env` 使用
