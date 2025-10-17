# bridge/demo_bridge.py
from bridge.bridge_ai import BridgeOrchestrator, BridgeConfig

if __name__ == "__main__":
    br = BridgeOrchestrator(BridgeConfig(
        openai_model="gpt-4o-mini",
        anthropic_model="claude-3-5-sonnet-20240620",
        temperature=0.2,
        max_tokens=400,
    ))

    prompt = "Explique le rôle des arbres urbains à Paris, en 5 points concrets."
    res = br.run(prompt, mode="claude_then_gpt")
    print("=== RÉSULTAT FINAL ===")
    print(res["text"])
    print("\n--- Étapes ---")
    for s in res["steps"]:
        print(f"[{s['provider']}] {s['text'][:120]}...")
        