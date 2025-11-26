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

def convert_to_command(user_prompt: str) -> str:
    prompt = f"""You are a Windows command line expert. Convert the natural language request to the exact Windows PowerShell command. Return ONLY the command, no explanations.

Rules:
- For creating empty files: use "type nul > filename.ext"
- For creating directories: use "mkdir dirname"
- For multiple commands: use semicolon (;) not &&
- For deleting files: use "del filename"
- For deleting directories: use "rmdir /s dirname"
- For listing files: use "dir"
- For copying files: use "copy source destination"

Examples:
Input: "make a directory called hello"
Output: mkdir hello

Input: "create a file named test.txt"
Output: type nul > test.txt

Input: "make an empty file called data.csv"
Output: type nul > data.csv

Input: "list all files"
Output: dir

Input: "delete file test.txt"
Output: del test.txt

Input: "delete directory hello"
Output: rmdir /s hello

Input: "copy file1.txt to file2.txt"
Output: copy file1.txt file2.txt

Now convert this request:
Input: "{user_prompt}"
Output:"""
    
    try:
        resp = client.chat_completion(
            messages=[{"role": "user", "content": prompt}], 
            max_tokens=100,
            temperature=0.1
        )
        result = resp.choices[0].message.content.strip()
        
        # Clean up the response - extract just the command
        lines = result.split('\n')
        for line in lines:
            line = line.strip()
            # Skip empty lines and lines that look like labels
            if line and not line.startswith('Input:') and not line.startswith('Output:') and not line.startswith('Examples:'):
                return line
        
        # If we get here, return the first non-empty line
        return result.split('\n')[0].strip() if result else "Error: No response from AI"
        
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        result = convert_to_command(user_input)
        print(result)
    else:
        print("Usage: python ai_convert.py <natural language request>")