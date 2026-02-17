#!/usr/bin/env python3
"""
Test a single BixBench question using ToolUniverse skills.

This script:
1. Loads a question from BixBench HuggingFace dataset
2. Downloads and extracts the capsule data
3. Calls the appropriate ToolUniverse skill
4. Compares result to ground truth

Usage:
    python test_single_question.py bix-13-q2
    python test_single_question.py bix-20-q2 --data-dir ./my_data
"""

import argparse
import ast
import shutil
from pathlib import Path
from typing import Any

from datasets import load_dataset
from huggingface_hub import hf_hub_download


class BixBenchTester:
    """Test ToolUniverse skills on BixBench questions."""

    def __init__(self, data_dir: Path = Path("./bixbench/data")):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load_question(self, question_id: str) -> dict[str, Any]:
        """
        Load a single question from BixBench dataset.

        Args:
            question_id: Question ID (e.g., "bix-13-q2")

        Returns:
            Question dictionary with all metadata
        """
        print(f"📥 Loading question {question_id} from HuggingFace...")

        dataset = load_dataset("futurehouse/BixBench", split="train")
        questions = [q for q in dataset if q["question_id"] == question_id]

        if not questions:
            available = [q["question_id"] for q in dataset][:10]
            raise ValueError(
                f"Question {question_id} not found. "
                f"Available (first 10): {available}"
            )

        question = questions[0]
        print(f"✅ Loaded: {question['short_id']}")
        print(f"📁 Category: {question['categories']}")
        return question

    def download_capsule_data(self, data_folder: str) -> Path:
        """
        Download and extract capsule data from HuggingFace.

        Reuses BixBench's data processing logic:
        - Downloads zip file
        - Extracts contents
        - Moves Data folder contents to root
        - Removes Notebook folders and .ipynb files

        Args:
            data_folder: Zip filename (e.g., "CapsuleFolder-xxx.zip")

        Returns:
            Path to extracted data directory
        """
        extract_dir = self.data_dir / data_folder.replace(".zip", "")

        # Check if already downloaded
        if extract_dir.exists() and any(extract_dir.iterdir()):
            print(f"✅ Data already exists: {extract_dir}")
            return extract_dir

        print(f"📥 Downloading capsule data: {data_folder}")

        # Download zip file from HuggingFace
        hf_hub_download(
            repo_id="futurehouse/BixBench",
            filename=data_folder,
            local_dir=self.data_dir,
            repo_type="dataset",
        )

        # Extract zip file
        zip_path = self.data_dir / data_folder
        print(f"📦 Extracting {zip_path}...")
        shutil.unpack_archive(zip_path, extract_dir)

        # Process extracted files (BixBench's logic)
        self._process_extracted_files(extract_dir)

        print(f"✅ Data ready: {extract_dir}")
        return extract_dir

    def _process_extracted_files(self, extract_dir: Path) -> None:
        """
        Process extracted capsule files (from BixBench code).

        1. Find Data folder
        2. Move its contents to root
        3. Remove Data folder
        4. Remove Notebook folders
        5. Remove .ipynb files
        """
        # Find and move Data folder contents
        data_folders = [
            p for p in extract_dir.rglob("*") if p.is_dir() and "Data" in p.name
        ]

        if data_folders:
            data_folder = data_folders[0]
            print(f"  Moving contents from {data_folder.name}...")
            for item in data_folder.iterdir():
                dest = extract_dir / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                shutil.move(str(item), str(dest))
            shutil.rmtree(data_folder)

        # Remove Notebook folders
        notebook_folders = [
            p for p in extract_dir.rglob("*") if p.is_dir() and "Notebook" in p.name
        ]
        for folder in notebook_folders:
            print(f"  Removing {folder.name}...")
            shutil.rmtree(folder)

        # Remove .ipynb files
        for ipynb in extract_dir.glob("*.ipynb"):
            print(f"  Removing {ipynb.name}...")
            ipynb.unlink()

    def list_data_files(self, data_dir: Path) -> list[Path]:
        """List all files in the data directory."""
        files = list(data_dir.rglob("*"))
        files = [f for f in files if f.is_file()]
        return sorted(files)

    def call_skill_for_question(self, question: dict, data_dir: Path) -> str:
        """
        Call the appropriate ToolUniverse skill for a question.

        This is a placeholder that shows how skills would be invoked.
        In practice, you'd use the Skill tool or direct skill invocation.

        Args:
            question: Question dictionary
            data_dir: Path to data files

        Returns:
            Answer string
        """
        category = question["categories"]
        question_text = question["question"]

        print(f"\n🤖 Determining appropriate skill...")
        print(f"   Category: {category}")

        # Map category to skill
        skill_mapping = {
            "differential_expression": "tooluniverse-rnaseq-deseq2",
            "RNA-seq": "tooluniverse-rnaseq-deseq2",
            "variant_analysis": "tooluniverse-variant-analysis",
            "Variant calling": "tooluniverse-variant-analysis",
            "single_cell": "tooluniverse-single-cell",
            "scRNA-seq": "tooluniverse-single-cell",
            "statistical": "tooluniverse-statistical-modeling",
            "Regression": "tooluniverse-statistical-modeling",
            "phylogenetics": "tooluniverse-phylogenetics",
            "Phylogenomics": "tooluniverse-phylogenetics",
            "image_analysis": "tooluniverse-image-analysis",
            "Microscopy": "tooluniverse-image-analysis",
            "Epigenomics": "tooluniverse-epigenomics",
        }

        skill = None
        for keyword, skill_name in skill_mapping.items():
            if keyword.lower() in category.lower():
                skill = skill_name
                break

        if not skill:
            print(f"⚠️  No skill found for category: {category}")
            print(f"   Would need to implement skill routing logic")
            return "SKILL_NOT_FOUND"

        print(f"✅ Selected skill: {skill}")
        print(f"\n📋 Skill would receive:")
        print(f"   - Question: {question_text}")
        print(f"   - Data dir: {data_dir}")
        print(f"   - Files: {len(list(data_dir.rglob('*')))} files")
        print(f"   - Hypothesis: {question['hypothesis'][:100]}...")

        # TODO: Actually invoke the skill
        # This would use the Skill tool or direct invocation
        # For now, return placeholder
        print(f"\n⚠️  Skill invocation not implemented yet")
        print(f"   This script currently only tests data loading")

        return "SKILL_NOT_IMPLEMENTED"

    def evaluate_answer(
        self, result: str, expected: str, eval_mode: str
    ) -> tuple[bool, str]:
        """
        Compare result to expected answer.

        Args:
            result: Skill's answer
            expected: Ground truth answer
            eval_mode: Evaluation method (str_verifier, range_verifier, llm_verifier)

        Returns:
            Tuple of (correct, explanation)
        """
        if eval_mode == "str_verifier":
            # Exact string match (case-insensitive, whitespace-stripped)
            result_clean = result.strip().lower()
            expected_clean = expected.strip().lower()
            correct = result_clean == expected_clean

            if correct:
                return True, f"Exact match: '{result}' == '{expected}'"
            else:
                return False, f"Mismatch: '{result}' != '{expected}'"

        elif eval_mode == "range_verifier":
            # Parse range like "(0.9, 1.0)" and check if result is in range
            try:
                result_num = float(result)
                range_tuple = ast.literal_eval(expected)
                correct = range_tuple[0] <= result_num <= range_tuple[1]

                if correct:
                    return True, f"{result_num} is in range {range_tuple}"
                else:
                    return False, f"{result_num} is outside range {range_tuple}"
            except (ValueError, SyntaxError) as e:
                return False, f"Error parsing numbers: {e}"

        elif eval_mode == "llm_verifier":
            # Would use LLM to compare
            # For now, just return placeholder
            return (
                False,
                f"LLM verification not implemented (result={result}, expected={expected})",
            )

        else:
            return False, f"Unknown eval_mode: {eval_mode}"

    def test_question(self, question_id: str) -> dict[str, Any]:
        """
        Test a single BixBench question.

        Args:
            question_id: Question ID (e.g., "bix-13-q2")

        Returns:
            Test results dictionary
        """
        print("=" * 80)
        print(f"TESTING BIXBENCH QUESTION: {question_id}")
        print("=" * 80)

        # Load question
        question = self.load_question(question_id)

        print(f"\n📝 Question:")
        print(f"   {question['question']}")
        print(f"\n🎯 Expected Answer: {question['ideal']}")
        print(f"📊 Evaluation Mode: {question['eval_mode']}")

        # Download data
        print(f"\n{'='*80}")
        print("DOWNLOADING DATA")
        print("=" * 80)
        data_dir = self.download_capsule_data(question["data_folder"])

        # List files
        files = self.list_data_files(data_dir)
        print(f"\n📁 Data files ({len(files)} total):")
        for f in files[:20]:  # Show first 20
            size = f.stat().st_size
            size_str = (
                f"{size:,} bytes" if size < 1024 else f"{size/1024:.1f} KB"
            )
            print(f"   - {f.name} ({size_str})")
        if len(files) > 20:
            print(f"   ... and {len(files)-20} more files")

        # Call skill
        print(f"\n{'='*80}")
        print("CALLING SKILL")
        print("=" * 80)
        result = self.call_skill_for_question(question, data_dir)

        # Evaluate
        print(f"\n{'='*80}")
        print("EVALUATION")
        print("=" * 80)
        correct, explanation = self.evaluate_answer(
            result, question["ideal"], question["eval_mode"]
        )

        print(f"\n{'✅ PASS' if correct else '❌ FAIL'}")
        print(f"Explanation: {explanation}")

        return {
            "question_id": question_id,
            "result": result,
            "expected": question["ideal"],
            "correct": correct,
            "explanation": explanation,
            "data_dir": str(data_dir),
            "files_count": len(files),
        }


def main():
    parser = argparse.ArgumentParser(
        description="Test a single BixBench question with ToolUniverse"
    )
    parser.add_argument("question_id", help="Question ID (e.g., bix-13-q2)")
    parser.add_argument(
        "--data-dir",
        default="./bixbench/data",
        help="Directory to store downloaded data",
    )
    args = parser.parse_args()

    tester = BixBenchTester(data_dir=Path(args.data_dir))
    result = tester.test_question(args.question_id)

    print(f"\n{'='*80}")
    print("SUMMARY")
    print("=" * 80)
    print(f"Question: {result['question_id']}")
    print(f"Result: {result['result']}")
    print(f"Expected: {result['expected']}")
    print(f"Status: {'✅ PASS' if result['correct'] else '❌ FAIL'}")
    print(f"Data: {result['data_dir']} ({result['files_count']} files)")


if __name__ == "__main__":
    main()
