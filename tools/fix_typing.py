#!/usr/bin/env python3
"""
Fix Typing Issues - Remove complex parameter typing for computational effectiveness
Converts strict typing to relaxed typing for better research/development workflow.
"""

import re
import os
from pathlib import Path

def fix_file_typing(filepath):
    """Remove complex parameter typing from a Python file."""
    
    print(f"🔧 Fixing typing in {filepath}...")
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Remove parameter type hints but keep defaults
        # Pattern: param: Type = default -> param=default
        content = re.sub(r'(\w+):\s*[A-Za-z_]\w*(?:\[[^\]]*\])?\s*(=)', r'\1\2', content)
        
        # Remove Optional parameter typing
        content = re.sub(r'(\w+):\s*Optional\[[^\]]+\]\s*(=)', r'\1\2', content)
        
        # Remove Union parameter typing  
        content = re.sub(r'(\w+):\s*Union\[[^\]]+\]\s*(=)', r'\1\2', content)
        
        # Remove complex parameter typing without defaults
        content = re.sub(r'(\w+):\s*[A-Za-z_]\w*(?:\[[^\]]*\])?(?=\s*[,)])', r'\1', content)
        
        # Remove return type hints that use undefined types (but keep simple ones)
        content = re.sub(r') -> Dict\[.*?\]:', r'):', content) 
        content = re.sub(r') -> List\[.*?\]:', r'):', content)
        content = re.sub(r') -> Optional\[.*?\]:', r'):', content)
        content = re.sub(r') -> Union\[.*?\]:', r'):', content)
        
        # Clean up any unused typing imports
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            # Skip lines that only import typing stuff we're not using
            if (line.startswith('from typing import') or 
                line.strip() == 'from typing import Optional, List, Dict, Any, Union, Tuple, Set'):
                # Check if any of these are used in return types or class definitions
                if not any(x in content for x in ['-> str', '-> int', '-> bool', '-> float']):
                    continue
            new_lines.append(line)
        
        content = '\n'.join(new_lines)
        
        # Only write if there were changes
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"✅ Fixed {filepath}")
            return True
        else:
            print(f"ℹ️ No changes needed for {filepath}")
            return False
            
    except Exception as e:
        print(f"❌ Error fixing {filepath}: {e}")
        return False

def main():
    """Fix typing issues in key source files."""
    
    print("🔧 GEX-LLM Typing Simplification Tool")
    print("=" * 50)
    print("Converting strict typing to relaxed typing for computational effectiveness")
    print()
    
    # Files to fix
    files_to_fix = [
        'src/data_sources/sample_data_loader.py',
        'src/agents/data_retrieval_agent.py', 
        'src/gex/sample_data_gex.py',
        'src/validation/options_data_validator.py',
        'src/llm/autogen_gex_analyzer.py'
    ]
    
    fixed_count = 0
    
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            if fix_file_typing(filepath):
                fixed_count += 1
        else:
            print(f"⚠️ File not found: {filepath}")
    
    print()
    print(f"✅ Completed! Fixed {fixed_count} files")
    print()
    print("📋 Benefits of simplified typing approach:")
    print("• Faster development iteration")
    print("• Fewer import-related errors")
    print("• More readable code")
    print("• Better for research/prototype projects")
    print("• Reduced cognitive overhead")
    print("• Computational effectiveness over strict typing")

if __name__ == '__main__':
    main()