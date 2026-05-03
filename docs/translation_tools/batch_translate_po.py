#!/usr/bin/env python3
"""
Batch Translation Script for .po files using AgenticTool

This script uses ToolUniverse's AgenticTool to batch translate .po files
from English to Chinese without modifying the source code.

Usage:
    python batch_translate_po.py --directory <path_to_po_files>
    python batch_translate_po.py --file <path_to_single_po_file>
    python batch_translate_po.py --status  # Show translation status

Author: ToolUniverse Community
Date: 2024
"""

import os
import sys
import json
import polib
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the src directory to the path so we can import ToolUniverse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tooluniverse import ToolUniverse
from tooluniverse.agentic_tool import AgenticTool


class POTranslator:
    """A simple .po file translator using AgenticTool."""
    
    def __init__(self, model_id: str = "gpt-4.1-mini", temperature: float = 0.3):
        """
        Initialize the translator.
        
        Args:
            model_id: OpenAI model to use for translation
            temperature: Temperature for translation (0.0-1.0)
        """
        self.model_id = model_id
        self.temperature = temperature
        self.tu = None
        self.translation_tool = None
        self._setup_tool()
    
    def _setup_tool(self):
        """Set up the AgenticTool for translation."""
        tool_config = {
            "name": "po_translator",
            "type": "AgenticTool",
            "description": "AI-powered translator for .po files",
            "prompt": """You are an expert translator specializing in technical documentation translation from English to Chinese.

Translate the following English text into natural, fluent Chinese while maintaining:
1. Technical accuracy and terminology consistency
2. Natural Chinese language flow
3. Professional documentation tone
4. Preserve any HTML tags or formatting

English text: {text}

Context: {context}

Provide only the Chinese translation without explanations:""",
            "input_arguments": ["text", "context"],
            "parameter": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "English text to translate"},
                    "context": {"type": "string", "description": "Translation context", "default": "Documentation"}
                },
                "required": ["text"]
            },
            "configs": {
                "api_type": "CHATGPT",
                "model_id": self.model_id,
                "temperature": self.temperature,
                "max_new_tokens": 2048,
                "return_json": False
            }
        }
        
        try:
            self.tu = ToolUniverse()
            self.translation_tool = AgenticTool(tool_config)
            print(f"✅ Translator initialized with model: {self.model_id}")
        except Exception as e:
            print(f"❌ Failed to initialize translator: {str(e)}")
            sys.exit(1)
    
    def translate_text(self, text: str, context: str = "Documentation") -> str:
        """Translate English text to Chinese."""
        try:
            result = self.translation_tool.run({"text": text, "context": context})
            
            if isinstance(result, str):
                translated = result.strip()
                # Remove any quotes that might be added by the LLM
                if translated.startswith('"') and translated.endswith('"'):
                    translated = translated[1:-1]
                return translated
            elif isinstance(result, dict) and result.get("success", False):
                # Handle the actual return format from AgenticTool
                translated = result.get("result", "").strip()
                if translated.startswith('"') and translated.endswith('"'):
                    translated = translated[1:-1]
                return translated
            else:
                print(f"❌ Translation failed: {result}")
                return text
                
        except Exception as e:
            print(f"❌ Translation error: {str(e)}")
            return text
    
    def get_po_stats(self, po_file_path: str) -> Dict[str, int]:
        """Get statistics for a .po file."""
        try:
            po = polib.pofile(po_file_path)
            total = len(po)
            translated = len([entry for entry in po if entry.msgstr])
            untranslated = total - translated
            return {
                "total": total,
                "translated": translated,
                "untranslated": untranslated,
                "completion": round((translated / total * 100) if total > 0 else 0, 1)
            }
        except Exception as e:
            print(f"❌ Error reading {po_file_path}: {str(e)}")
            return {"total": 0, "translated": 0, "untranslated": 0, "completion": 0}
    
    def translate_po_file(self, po_file_path: str, max_entries: Optional[int] = None, 
                         context: str = "Documentation") -> bool:
        """
        Translate untranslated entries in a .po file.
        
        Args:
            po_file_path: Path to the .po file
            max_entries: Maximum number of entries to translate (None for all)
            context: Translation context
            
        Returns:
            True if successful, False otherwise
        """
        print(f"\n🔄 Processing: {po_file_path}")
        
        try:
            po = polib.pofile(po_file_path)
            
            # Find untranslated entries
            untranslated = [entry for entry in po if not entry.msgstr and entry.msgid]
            
            if not untranslated:
                print("✅ No untranslated entries found")
                return True
            
            # Limit entries if specified
            if max_entries:
                untranslated = untranslated[:max_entries]
            
            print(f"📝 Found {len(untranslated)} untranslated entries")
            
            # Translate entries
            translated_count = 0
            for i, entry in enumerate(untranslated, 1):
                print(f"🔄 [{i}/{len(untranslated)}] Translating: {entry.msgid[:60]}...")
                
                translated_text = self.translate_text(entry.msgid, context)
                
                if translated_text and translated_text != entry.msgid:
                    entry.msgstr = translated_text
                    translated_count += 1
                    print(f"✅ Translated: {translated_text[:60]}...")
                else:
                    print(f"⚠️  Skipped (no translation)")
            
            # Save the file
            po.save()
            print(f"✅ Updated {translated_count} entries in {po_file_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error processing {po_file_path}: {str(e)}")
            return False
    
    def batch_translate(self, directory_path: str, max_entries_per_file: Optional[int] = None,
                       context: str = "Documentation", exclude_dirs: Optional[list] = None) -> Dict[str, bool]:
        """Translate all .po files in a directory."""
        results = {}
        exclude_dirs = set(exclude_dirs or [])
        po_files = [
            f for f in Path(directory_path).rglob("*.po")
            if not any(part in exclude_dirs for part in f.relative_to(directory_path).parts)
        ]

        if not po_files:
            print(f"❌ No .po files found in {directory_path}")
            return results

        print(f"📁 Found {len(po_files)} .po files")

        for i, po_file in enumerate(po_files, 1):
            print(f"\n[{i}/{len(po_files)}] {po_file.relative_to(directory_path)}")
            success = self.translate_po_file(str(po_file), max_entries_per_file, context)
            results[str(po_file)] = success

        return results

    def show_status(self, directory_path: str, exclude_dirs: Optional[list] = None):
        """Show translation status for all .po files in a directory."""
        exclude_dirs = set(exclude_dirs or [])
        po_files = [
            f for f in Path(directory_path).rglob("*.po")
            if not any(part in exclude_dirs for part in f.relative_to(directory_path).parts)
        ]
        
        if not po_files:
            print(f"❌ No .po files found in {directory_path}")
            return
        
        print(f"📊 Translation Status for {len(po_files)} .po files:")
        print("=" * 80)
        print(f"{'File':<50} {'Total':<8} {'Done':<8} {'Remaining':<10} {'%':<6}")
        print("-" * 80)
        
        total_stats = {"total": 0, "translated": 0, "untranslated": 0}
        
        for po_file in sorted(po_files):
            stats = self.get_po_stats(str(po_file))
            total_stats["total"] += stats["total"]
            total_stats["translated"] += stats["translated"]
            total_stats["untranslated"] += stats["untranslated"]
            
            filename = po_file.name
            if len(filename) > 47:
                filename = "..." + filename[-44:]
            
            print(f"{filename:<50} {stats['total']:<8} {stats['translated']:<8} "
                  f"{stats['untranslated']:<10} {stats['completion']:<6}%")
        
        print("-" * 80)
        overall_completion = round((total_stats["translated"] / total_stats["total"] * 100) 
                                 if total_stats["total"] > 0 else 0, 1)
        print(f"{'TOTAL':<50} {total_stats['total']:<8} {total_stats['translated']:<8} "
              f"{total_stats['untranslated']:<10} {overall_completion:<6}%")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Batch translate .po files using AgenticTool")
    parser.add_argument("--directory", "-d", help="Directory containing .po files")
    parser.add_argument("--file", "-f", help="Single .po file to translate")
    parser.add_argument("--status", "-s", action="store_true", help="Show translation status")
    parser.add_argument("--max-entries", "-m", type=int, help="Maximum entries to translate per file")
    parser.add_argument("--model", default="gpt-4.1-mini", help="OpenAI model to use")
    parser.add_argument("--temperature", type=float, default=0.3, help="Translation temperature")
    parser.add_argument("--context", default="Documentation", help="Translation context")
    parser.add_argument("--exclude", "-x", nargs="+", default=[], metavar="DIR",
                        help="Subdirectory names to exclude (e.g. api old_files tutorials)")

    args = parser.parse_args()
    
    # Default to locale directory if no arguments provided
    if not any([args.directory, args.file, args.status]):
        locale_dir = Path(__file__).parent / "locale" / "zh_CN" / "LC_MESSAGES"
        if locale_dir.exists():
            args.directory = str(locale_dir)
        else:
            print("❌ No directory specified and no default locale directory found")
            parser.print_help()
            sys.exit(1)
    
    # Initialize translator
    translator = POTranslator(model_id=args.model, temperature=args.temperature)
    
    if args.status:
        # Show status
        if args.directory:
            translator.show_status(args.directory, exclude_dirs=args.exclude)
        elif args.file:
            stats = translator.get_po_stats(args.file)
            print(f"📊 Status for {args.file}:")
            print(f"  Total entries: {stats['total']}")
            print(f"  Translated: {stats['translated']}")
            print(f"  Untranslated: {stats['untranslated']}")
            print(f"  Completion: {stats['completion']}%")
    else:
        # Translate files
        if args.file:
            success = translator.translate_po_file(args.file, args.max_entries, args.context)
            if success:
                print("✅ Translation completed successfully!")
            else:
                print("❌ Translation failed!")
                sys.exit(1)
        elif args.directory:
            results = translator.batch_translate(args.directory, args.max_entries, args.context,
                                                  exclude_dirs=args.exclude)
            successful = sum(1 for success in results.values() if success)
            print(f"\n📊 Summary: {successful}/{len(results)} files processed successfully")
            
            if successful < len(results):
                print("❌ Some files failed to process")
                sys.exit(1)


if __name__ == "__main__":
    main()
