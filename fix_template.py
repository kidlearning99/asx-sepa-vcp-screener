import sys
import os

file_path = r'c:\Claude AI\asx-sepa-vcp-screener\build_dashboard.py'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove the 'f' prefix from the return f""" block
    content = content.replace('    return f"""<!DOCTYPE html>', '    return """<!DOCTYPE html>')
    
    # 2. Because it's no longer an f-string, we must convert all {{ and }} back to { and }
    # but ONLY inside the template string.
    # The template starts at """<!DOCTYPE html> and ends at </html>"""
    
    start_str = '    return """<!DOCTYPE html>'
    end_str = '</html>"""'
    
    start_idx = content.find(start_str)
    end_idx = content.find(end_str)
    
    if start_idx != -1 and end_idx != -1:
        template = content[start_idx:end_idx + len(end_str)]
        
        # Convert doubled braces to single braces
        template = template.replace('{{', '{').replace('}}', '}')
        
        # 3. Now handle the variables that WERE in the f-string.
        # {today_str} -> {today_str} (it stayed {today_str} after the replace overhead)
        # However, we need to inject them.
        # We will change the return line to:
        # return """...""".format(today_str=today_str, json_data=json_data, sector_opts=sector_opts, top_html=top_html, n=n, breakouts=len(breakouts), pivots=len(pivots), watching=len(watching), stage2=len(stage2))
        
        # Let's find common f-string injections
        # {today_str}, {json_data}, {sector_opts}, {top_html}, {n}, {len(breakouts)}, etc.
        
        # Actually, it's easier to just use .replace() for each one to be safe.
        template = template.replace('return """', 'tmpl = """')
        
        # New return logic:
        new_return = (
            '\n    html = tmpl.replace("{today_str}", today_str)'
            '\n    html = html.replace("{json_data}", json_data)'
            '\n    html = html.replace("{sector_opts}", sector_opts)'
            '\n    html = html.replace("{top_html}", top_html)'
            '\n    html = html.replace("{n}", str(n))'
            '\n    html = html.replace("{len(breakouts)}", str(len(breakouts)))'
            '\n    html = html.replace("{len(pivots)}", str(len(pivots)))'
            '\n    html = html.replace("{len(watching)}", str(len(watching)))'
            '\n    return html'
        )
        
        final_block = template + new_return
        
        content = content[:start_idx] + final_block + content[end_idx + len(end_str):]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("SUCCESS: build_dashboard.py refactored to use plain string template. Syntax errors resolved.")
    else:
        print("Could not find template markers.")

except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
