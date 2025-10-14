# check_path.py
import sys
print("Python executable:")
print(sys.executable)
print("\nPython path:")
for path in sys.path:
    print(f"  - {path}")

print("\n---")
import os
print(f"Current directory: {os.getcwd()}")
print(f"Script directory: {os.path.dirname(__file__)}")
