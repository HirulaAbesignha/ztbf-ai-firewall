"""Quick fix for Unicode and missing method issues"""

import os

# Fix 1: Update queue.py to remove emojis
queue_file = "src/data_pipeline/ingestion/queue.py"
if os.path.exists(queue_file):
    with open(queue_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace emojis
    content = content.replace('💾', '')
    content = content.replace('🔄', '')
    content = content.replace('✅', '')
    content = content.replace('📦', '')
    content = content.replace('⚠️', '')
    content = content.replace('🗑️', '')
    
    with open(queue_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Fixed queue.py emojis")

# Fix 2: Check if enricher has the method
enricher_file = "src/data_pipeline/processing/enricher.py"
if os.path.exists(enricher_file):
    with open(enricher_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '_load_sensitivity_rules' not in content:
        print("! enricher.py is missing _load_sensitivity_rules method")
        print("! Please add the method manually (see instructions above)")
    else:
        print("✓ enricher.py has _load_sensitivity_rules method")

print("\nDone! Now run the processor again.")