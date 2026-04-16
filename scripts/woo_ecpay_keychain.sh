#!/usr/bin/env bash
ECPAY_MERCHANT_ID=$(security find-generic-password -a "$USER" -s ecpay-merchant-id -w 2>/dev/null) || {
  echo "ERROR: ecpay-merchant-id not in keychain. Run: /woo-orders setup" >&2
  exit 2
}
ECPAY_HASH_KEY=$(security find-generic-password -a "$USER" -s ecpay-hash-key -w 2>/dev/null) || {
  echo "ERROR: ecpay-hash-key not in keychain. Run: /woo-orders setup" >&2
  exit 2
}
ECPAY_HASH_IV=$(security find-generic-password -a "$USER" -s ecpay-hash-iv -w 2>/dev/null) || {
  echo "ERROR: ecpay-hash-iv not in keychain. Run: /woo-orders setup" >&2
  exit 2
}
ECPAY_SENDER_NAME=$(security find-generic-password -a "$USER" -s ecpay-sender-name -w 2>/dev/null) || {
  echo "ERROR: ecpay-sender-name not in keychain. Run: /woo-orders setup" >&2
  exit 2
}
# Hex-decode if macOS Keychain returned hex-encoded bytes for non-ASCII value
if [[ "$ECPAY_SENDER_NAME" =~ ^[0-9a-f]+$ ]] && (( ${#ECPAY_SENDER_NAME} % 2 == 0 )); then
  decoded=$(echo "$ECPAY_SENDER_NAME" | xxd -r -p 2>/dev/null) && [ -n "$decoded" ] && ECPAY_SENDER_NAME="$decoded"
fi
ECPAY_SENDER_PHONE=$(security find-generic-password -a "$USER" -s ecpay-sender-phone -w 2>/dev/null) || {
  echo "ERROR: ecpay-sender-phone not in keychain. Run: /woo-orders setup" >&2
  exit 2
}
# Hex-decode if macOS Keychain returned hex-encoded bytes for non-ASCII value
if [[ "$ECPAY_SENDER_PHONE" =~ ^[0-9a-f]+$ ]] && (( ${#ECPAY_SENDER_PHONE} % 2 == 0 )); then
  decoded=$(echo "$ECPAY_SENDER_PHONE" | xxd -r -p 2>/dev/null) && [ -n "$decoded" ] && ECPAY_SENDER_PHONE="$decoded"
fi
ECPAY_SENDER_CELLPHONE=$(security find-generic-password -a "$USER" -s ecpay-sender-cellphone -w 2>/dev/null) || {
  echo "ERROR: ecpay-sender-cellphone not in keychain. Run: /woo-orders setup" >&2
  exit 2
}
# Hex-decode if macOS Keychain returned hex-encoded bytes for non-ASCII value
if [[ "$ECPAY_SENDER_CELLPHONE" =~ ^[0-9a-f]+$ ]] && (( ${#ECPAY_SENDER_CELLPHONE} % 2 == 0 )); then
  decoded=$(echo "$ECPAY_SENDER_CELLPHONE" | xxd -r -p 2>/dev/null) && [ -n "$decoded" ] && ECPAY_SENDER_CELLPHONE="$decoded"
fi
export ECPAY_MERCHANT_ID ECPAY_HASH_KEY ECPAY_HASH_IV ECPAY_SENDER_NAME ECPAY_SENDER_PHONE ECPAY_SENDER_CELLPHONE
