from pathlib import Path

data = Path("requirements.txt").read_bytes()
print(list(data[:16]))
print(data[:3])
