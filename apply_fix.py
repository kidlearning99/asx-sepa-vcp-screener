import sys
import os

def fix():
    target_file = r'c:\Claude AI\asx-sepa-vcp-screener\build_dashboard.py'
    new_det_file = r'c:\Claude AI\asx-sepa-vcp-screener\new_det.txt'
    
    if not os.path.exists(new_det_file):
        print("Missing new_det.txt")
        return

    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(new_det_file, 'r', encoding='utf-8') as f:
        new_det_body = f.read()

    # We need to find the old det(r) function and replace it.
    # Start: function det(r){{
    # End: the }} before function tog(i)
    
    start_marker = "function det(r){{"
    end_marker = "\n\nfunction tog(i)"
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print(f"Could not find markers. Start: {start_idx}, End: {end_idx}")
        return

    # Look for the last }} before end_marker
    func_end = content.rfind("}}", start_idx, end_idx) + 2
    
    new_content = content[:start_idx] + new_det_body + content[func_end:]
    
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("SUCCESS: Fixed build_dashboard.py with the correct UI logic.")

if __name__ == "__main__":
    fix()
