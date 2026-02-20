"""Fix test_pipeline.py issues"""
import re

file_path = "scripts/test_pipeline.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Replace datetime.utcnow() with datetime.now(datetime.UTC)
content = content.replace('datetime.utcnow()', 'datetime.now(datetime.UTC)')

# Fix 2: Increase wait time for storage
content = re.sub(
    r'print\(f"   Waiting 10 seconds for processing\.\.\."\)\s+await asyncio\.sleep\(10\)',
    'print(f"   Waiting 30 seconds for processing...")\n        await asyncio.sleep(30)',
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed test_pipeline.py")
print("\nNow:")
print("1. Start processor: python src/data_pipeline/processing/processor.py --workers 8")
print("2. Wait 5 seconds")
print("3. Run tests: python scripts/test_pipeline.py")