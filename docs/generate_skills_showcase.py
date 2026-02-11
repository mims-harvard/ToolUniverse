#!/usr/bin/env python3
"""
Generate skills showcase documentation from skills directory.
Automatically updates when skills are added/modified.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

def parse_skill_frontmatter(skill_path: Path) -> Dict[str, str]:
    """Extract name and description from SKILL.md frontmatter."""
    try:
        with open(skill_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract frontmatter between --- markers
        match = re.search(r'^---\s*\n(.*?)\n---', content, re.MULTILINE | re.DOTALL)
        if not match:
            return {}
        
        frontmatter = match.group(1)
        
        # Parse name and description
        name_match = re.search(r'^name:\s*(.+)$', frontmatter, re.MULTILINE)
        desc_match = re.search(r'^description:\s*(.+)$', frontmatter, re.MULTILINE | re.DOTALL)
        
        name = name_match.group(1).strip() if name_match else None
        description = desc_match.group(1).strip() if desc_match else None
        
        # Clean up description (remove extra whitespace)
        if description:
            description = ' '.join(description.split())
        
        return {
            'name': name,
            'description': description
        }
    except Exception as e:
        print(f"Warning: Could not parse {skill_path}: {e}")
        return {}

def categorize_skills(skills: List[Tuple[str, Dict]]) -> Dict[str, List[Tuple[str, Dict]]]:
    """Categorize skills by type."""
    categories = {
        'Research Skills': [],
        'Development Skills': [],
        'Setup & Configuration': [],
        'General Purpose': []
    }
    
    for skill_dir, info in skills:
        if skill_dir.startswith('devtu-'):
            categories['Development Skills'].append((skill_dir, info))
        elif skill_dir.startswith('setup-'):
            categories['Setup & Configuration'].append((skill_dir, info))
        elif skill_dir == 'tooluniverse':
            categories['General Purpose'].append((skill_dir, info))
        else:
            categories['Research Skills'].append((skill_dir, info))
    
    return categories

def generate_skills_showcase() -> str:
    """Generate RST content for skills showcase."""
    
    # Find all skills
    skills_dir = Path(__file__).parent.parent / 'skills'
    skills = []
    
    for item in sorted(skills_dir.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            skill_file = item / 'SKILL.md'
            if skill_file.exists():
                info = parse_skill_frontmatter(skill_file)
                if info.get('name'):
                    skills.append((item.name, info))
    
    # Categorize skills
    categories = categorize_skills(skills)
    
    # Generate RST
    rst_content = """AI Agent Skills
================

**Specialized research workflows for ToolUniverse**

ToolUniverse provides AI agent skills that teach agents how to conduct sophisticated scientific research. These skills combine multiple tools into expert-level workflows.

.. important:: **Install all skills with one command:**

   .. code-block:: bash
   
      npx skills add mims-harvard/ToolUniverse

"""
    
    # Add each category in specific order (Setup/General first, then Research, then Development at bottom)
    category_order = ['Setup & Configuration', 'General Purpose', 'Research Skills', 'Development Skills']
    
    for category in category_order:
        category_skills = categories.get(category, [])
        if not category_skills:
            continue
        
        rst_content += f"\n{category}\n"
        rst_content += "-" * len(category) + "\n\n"
        
        # Calculate grid columns based on number of skills
        num_skills = len(category_skills)
        if num_skills <= 2:
            grid_cols = "1 1 2 2"
        elif num_skills <= 3:
            grid_cols = "1 1 2 3"
        else:
            grid_cols = "1 1 2 3"
        
        rst_content += f".. grid:: {grid_cols}\n"
        rst_content += "   :gutter: 3\n\n"
        
        for skill_dir, info in category_skills:
            name = info['name']
            description = info['description']
            
            # Use cleaner display name (remove 'tooluniverse-' prefix for brevity)
            display_name = name
            if skill_dir.startswith('tooluniverse-'):
                # Convert kebab-case to Title Case for better readability
                clean_name = skill_dir.replace('tooluniverse-', '').replace('-', ' ').title()
                display_name = clean_name
            elif skill_dir.startswith('devtu-'):
                clean_name = skill_dir.replace('devtu-', '').replace('-', ' ').title()
                display_name = f"DevTU: {clean_name}"
            elif skill_dir.startswith('setup-'):
                clean_name = skill_dir.replace('setup-', '').replace('-', ' ').title()
                display_name = f"Setup: {clean_name}"
            
            # Truncate long descriptions
            if len(description) > 150:
                description = description[:147] + "..."
            
            # Determine icon based on skill type
            if 'drug' in skill_dir.lower():
                icon = "💊"
            elif 'protein' in skill_dir.lower():
                icon = "🧬"
            elif 'disease' in skill_dir.lower():
                icon = "🏥"
            elif 'literature' in skill_dir.lower():
                icon = "📚"
            elif 'target' in skill_dir.lower():
                icon = "🎯"
            elif 'sequence' in skill_dir.lower():
                icon = "🧬"
            elif 'structure' in skill_dir.lower():
                icon = "🔬"
            elif 'variant' in skill_dir.lower():
                icon = "🧬"
            elif 'expression' in skill_dir.lower():
                icon = "📊"
            elif 'chemical' in skill_dir.lower() or 'compound' in skill_dir.lower():
                icon = "🧪"
            elif 'binder' in skill_dir.lower():
                icon = "🔗"
            elif 'therapeutic' in skill_dir.lower():
                icon = "💉"
            elif 'oncology' in skill_dir.lower() or 'precision' in skill_dir.lower():
                icon = "🎗️"
            elif 'pharmacovigilance' in skill_dir.lower():
                icon = "⚠️"
            elif 'infectious' in skill_dir.lower():
                icon = "🦠"
            elif 'rare' in skill_dir.lower():
                icon = "🔍"
            elif 'repurposing' in skill_dir.lower():
                icon = "♻️"
            elif 'sdk' in skill_dir.lower():
                icon = "🐍"
            elif 'setup' in skill_dir.lower():
                icon = "⚙️"
            elif 'devtu' in skill_dir.lower():
                icon = "🛠️"
            else:
                icon = "✨"
            
            # GitHub link for the skill
            github_url = f"https://github.com/mims-harvard/ToolUniverse/tree/main/skills/{skill_dir}"
            
            rst_content += f"   .. grid-item-card:: {icon} {display_name}\n"
            rst_content += f"      :link: {github_url}\n"
            rst_content += "      :class-card: hover-lift\n"
            rst_content += "      :shadow: md\n"
            rst_content += "      \n"
            rst_content += f"      {description}\n"
            rst_content += "      \n"
            rst_content += "      +++\n"
            rst_content += "      \n"
            rst_content += f"      :bdg-info:`{skill_dir}`\n\n"
    
    # Add usage section
    rst_content += """
How to Use Skills
-----------------

After installation, skills are available in your AI coding agent. Some agents activate skills automatically based on your questions, while others may require you to explicitly mention the skill name.

.. grid:: 1 1 2 2
   :gutter: 3

   .. grid-item-card:: 💊 Drug Research
      :class-card: hover-lift
      :shadow: sm
      
      **Ask**: "Research aspirin comprehensively"
      
      **Activates**: tooluniverse-drug-research

   .. grid-item-card:: 🎯 Target Analysis
      :class-card: hover-lift
      :shadow: sm
      
      **Ask**: "Analyze EGFR as a drug target"
      
      **Activates**: tooluniverse-target-research

   .. grid-item-card:: 🏥 Disease Investigation
      :class-card: hover-lift
      :shadow: sm
      
      **Ask**: "Generate disease report for diabetes"
      
      **Activates**: tooluniverse-disease-research

   .. grid-item-card:: 📚 Literature Review
      :class-card: hover-lift
      :shadow: sm
      
      **Ask**: "Deep literature review on CRISPR"
      
      **Activates**: tooluniverse-literature-deep-research

"""
    
    return rst_content

if __name__ == '__main__':
    output_file = Path(__file__).parent / 'skills_showcase.rst'
    content = generate_skills_showcase()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Generated {output_file}")
    print(f"📊 Total skills documented: {content.count('grid-item-card')}")
