import sys
import httpx
from openai import OpenAI
import logging

logging.basicConfig(level=logging.DEBUG)

def debug_connection(base_url, api_key, model):
    print(f"--- Testing Config ---")
    print(f"BaseURL: {base_url}")
    print(f"Key: {api_key[:5]}...{api_key[-3:] if len(api_key)>8 else ''}")
    print(f"Model: {model}")
    
    try:
        # Test 1: Raw HTTPX Ping
        print("\n[Phase 1] Raw HTTPX Ping to /chat/completions")
        with httpx.Client(timeout=15.0, verify=False) as client:
            resp = client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Return OK"}],
                    "max_tokens": 5
                }
            )
            print(f"Raw Status: {resp.status_code}")
            print(f"Raw Text: {resp.text}")
    except Exception as e:
        print(f"Raw HTTPX Failed: {e}")

    try:
        # Test 2: OpenAI Package
        print("\n[Phase 2] OpenAI SDK Wrapper Ping")
        oc = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=httpx.Client(timeout=httpx.Timeout(15.0, connect=5.0), verify=False)
        )
        resp2 = oc.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Return OK"}],
            max_tokens=5
        )
        print(f"SDK Response Choices: {resp2.choices}")
    except Exception as e:
        print(f"SDK Failed: {type(e).__name__} - {e}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python debug_llm.py <base_url> <key> <model>")
    else:
        debug_connection(sys.argv[1], sys.argv[2], sys.argv[3])
