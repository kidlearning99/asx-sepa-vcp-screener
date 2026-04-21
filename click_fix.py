import sys
import os

def fix():
    target_file = r'c:\Claude AI\asx-sepa-vcp-screener\build_dashboard.py'
    
    with open(target_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Step 1: Add missing .replace() calls for stage counts
    # We find line 775: html = html.replace("{len(watching)}", str(len(watching)))
    # and add stage counts.
    
    new_replacements = [
        '    html = html.replace("{len(stage1)}", str(len(stage1)))',
        '    html = html.replace("{len(stage2)}", str(len(stage2)))',
        '    html = html.replace("{len(stage3)}", str(len(stage3)))',
        '    html = html.replace("{len(stage4)}", str(len(stage4)))'
    ]
    
    found_idx = -1
    for i, line in enumerate(lines):
        if 'html.replace("{len(watching)}"' in line:
            found_idx = i
            break
    
    if found_idx != -1:
        lines = lines[:found_idx+1] + [l + '\n' for l in new_replacements] + lines[found_idx+1:]

    # Step 2: Inject SLBL and SDESC into JS
    # We find the start of the <script> block and add them.
    js_consts = """
var SLBL = {1: 'S1 Neglect', 2: 'S2 Advancing', 3: 'S3 Topping', 4: 'S4 Declining'};
var SDESC = {
  1: 'Stock is basing after a long downtrend. Wait for Stage 2.',
  2: 'Uptrend confirmed. Institutions are buying. Target entry.',
  3: 'Momentum slowing. Heavy volume on down days. Sell/Reduce.',
  4: 'Downtrend in progress. Avoid or Short.'
};
"""
    for i, line in enumerate(lines):
        if '<script>' in line:
            lines[i] = line + js_consts
            break

    # Step 3: Define stageBox inside det(r)
    # Find var crows = ... and insert stageBox after it.
    stage_box_def = """
  var stageBox='<div class="stage-info-box" style="color:'+sc2+';background:'+sc2+'0d;border-color:'+sc2+'33">'+
    '<strong>'+SLBL[stg]+'</strong> \\u2014 '+SDESC[stg]+
    '</div>';
"""
    for i, line in enumerate(lines):
        if 'var crows=' in line:
            lines[i] = line + stage_box_def
            break

    with open(target_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("SUCCESS: Dashboard click fix applied.")

if __name__ == "__main__":
    fix()
