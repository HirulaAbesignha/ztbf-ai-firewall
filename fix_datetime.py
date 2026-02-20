"""Fix datetime compatibility issue"""

file_path = "scripts/test_pipeline.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace datetime.now(datetime.UTC) with datetime.utcnow()
content = content.replace('datetime.now(datetime.UTC)', 'datetime.utcnow()')

# Also add timezone import at the top if needed
if 'from datetime import' in content and 'timezone' not in content:
    content = content.replace(
        'from datetime import datetime, timedelta',
        'from datetime import datetime, timedelta, timezone'
    )

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed datetime.UTC issue")
print("✓ Reverted to datetime.utcnow()")
print("\nNow run: python scripts/test_pipeline.py")