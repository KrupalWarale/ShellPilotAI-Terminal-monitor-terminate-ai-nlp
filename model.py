#!/usr/bin/env python3
import os
import sys
from huggingface_hub import InferenceClient
from dotenv import load_dotenv, find_dotenv

# Load .env if present
load_dotenv(find_dotenv())

MODEL = "meta-llama/Llama-3.1-8B-Instruct"

# Accept either HF_TOKEN or HUGGINGFACEHUB_API_TOKEN
token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
if not token:
	sys.exit("Set HF_TOKEN or HUGGINGFACEHUB_API_TOKEN")

client = InferenceClient(MODEL, token=token)

# Seed from CLI args, then enter REPL
seed = " ".join(sys.argv[1:]).strip()

def run_once(user_prompt: str) -> None:
	resp = client.chat_completion(messages=[{"role": "user", "content": user_prompt}], max_tokens=512)
	try:
		print(resp.choices[0].message.content)
	except Exception:
		print("")

if seed:
	run_once(seed)

while True:
	try:
		user_input = input("> ").strip()
	except (EOFError, KeyboardInterrupt):
		break
	if not user_input or user_input.lower() in ("exit", "quit"):
		break
	run_once(user_input) 