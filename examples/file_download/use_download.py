#!/usr/bin/env python3
"""
File Download Tools - Comprehensive Usage Examples

This example demonstrates the three file download tools:
1. FileDownloadTool - Most flexible, saves or returns content
2. BinaryDownloadTool - Optimized for large binary files
3. TextDownloadTool - Returns text content directly

Each tool is demonstrated with practical examples.
"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from tooluniverse.file_download_tool import FileDownloadTool, BinaryDownloadTool, TextDownloadTool


def example_1_basic_download():
    """Example 1: Basic file download to temporary directory"""
    print("\n" + "=" * 70)
    print("Example 1: Basic File Download (auto save to temp directory)")
    print("=" * 70)

    config = {"name": "download_file"}
    tool = FileDownloadTool(config)

    # Download a sample JSON file (no output_path specified)
    url = "https://jsonplaceholder.typicode.com/posts/1"
    result = tool.run({"url": url, "timeout": 30})

    if "file_path" in result:
        print(f"✓ File downloaded successfully!")
        print(f"  Location: {result['file_path']}")
        print(f"  Size: {result['file_size']} bytes")
        print(f"  Type: {result['content_type']}")

        # Read and display content
        with open(result['file_path']) as f:
            data = json.load(f)
            print(f"\n  Content preview:")
            print(f"  Title: {data.get('title', 'N/A')[:50]}...")
            print(f"  User ID: {data.get('userId', 'N/A')}")
        return True
    else:
        print(f"✗ Error: {result.get('error', 'Unknown')}")
        return False


def example_2_custom_path():
    """Example 2: Download to custom path with directory creation"""
    print("\n" + "=" * 70)
    print("Example 2: Download to Custom Path")
    print("=" * 70)

    config = {"name": "download_file"}
    tool = FileDownloadTool(config)

    # Download to a specific path
    output_path = "./downloaded_data/example.json"
    url = "https://jsonplaceholder.typicode.com/posts/2"

    result = tool.run({
        "url": url,
        "output_path": output_path,
        "timeout": 30
    })

    if "file_path" in result:
        print(f"✓ File downloaded to custom location!")
        print(f"  Path: {result['file_path']}")
        print(f"  Size: {result['file_size']} bytes")
        print(f"  Note: Parent directories created automatically")
        return True
    else:
        print(f"✗ Error: {result.get('error', 'Unknown')}")
        return False


def example_3_return_content():
    """Example 3: Download and return content directly without saving"""
    print("\n" + "=" * 70)
    print("Example 3: Return Content Directly (No File Save)")
    print("=" * 70)

    config = {"name": "download_file"}
    tool = FileDownloadTool(config)

    # Download and return content directly
    url = "https://jsonplaceholder.typicode.com/posts/3"
    result = tool.run({
        "url": url,
        "return_content": True,
        "timeout": 30
    })

    if "content" in result:
        print(f"✓ Content downloaded successfully!")
        print(f"  Size: {result['size']} bytes")
        print(f"  Type: {result['content_type']}")

        # Parse JSON content
        data = json.loads(result['content'])
        print(f"\n  Parsed JSON data:")
        print(f"  Post ID: {data.get('id', 'N/A')}")
        print(f"  Title: {data.get('title', 'N/A')[:60]}...")
        print(f"  Body: {data.get('body', 'N/A')[:60]}...")
        return True
    else:
        print(f"✗ Error: {result.get('error', 'Unknown')}")
        return False


def example_4_binary_download():
    """Example 4: Download large binary file"""
    print("\n" + "=" * 70)
    print("Example 4: Download Binary File (Optimized for Large Files)")
    print("=" * 70)

    config = {"name": "download_binary"}
    tool = BinaryDownloadTool(config)

    # Download an image (binary file)
    url = "https://httpbin.org/image/jpeg"
    output_path = "./downloaded_data/test_image.jpg"

    result = tool.run({
        "url": url,
        "output_path": output_path,
        "timeout": 30
    })

    if "file_path" in result:
        print(f"✓ Binary file downloaded successfully!")
        print(f"  Path: {result['file_path']}")
        print(f"  Size: {result['size']} bytes")
        print(f"  Type: {result['content_type']}")
        print(f"  HTTP Status: {result['status_code']}")

        # Show size in human-readable format
        size_kb = result['size'] / 1024
        if size_kb < 1024:
            print(f"  Size: {size_kb:.2f} KB")
        else:
            print(f"  Size: {size_kb/1024:.2f} MB")
        return True
    else:
        print(f"✗ Error: {result.get('error', 'Unknown')}")
        return False


def example_5_text_download():
    """Example 5: Download text content with automatic encoding"""
    print("\n" + "=" * 70)
    print("Example 5: Download Text Content (Auto Encoding Detection)")
    print("=" * 70)

    config = {"name": "download_text"}
    tool = TextDownloadTool(config)

    # Download text file
    url = "https://httpbin.org/robots.txt"
    result = tool.run({"url": url, "timeout": 30})

    if "content" in result:
        print(f"✓ Text content downloaded successfully!")
        print(f"  Size: {result['size']} characters")
        print(f"  Encoding: {result['encoding']}")
        print(f"  Type: {result['content_type']}")

        # Show content preview
        print(f"\n  Content preview (first 10 lines):")
        lines = result['content'].split('\n')[:10]
        for i, line in enumerate(lines, 1):
            print(f"  {i}: {line}")
        return True
    else:
        print(f"✗ Error: {result.get('error', 'Unknown')}")
        return False


def example_6_custom_timeout():
    """Example 6: Download with custom timeout and chunk size"""
    print("\n" + "=" * 70)
    print("Example 6: Download with Custom Timeout and Chunk Size")
    print("=" * 70)

    config = {"name": "download_file"}
    tool = FileDownloadTool(config)

    # Download with custom settings for large file
    url = "https://jsonplaceholder.typicode.com/posts"
    result = tool.run({
        "url": url,
        "output_path": "./downloaded_data/all_posts.json",
        "timeout": 60,  # 60 seconds timeout
        "chunk_size": 16384,  # 16KB chunks (larger for bigger files)
        "follow_redirects": True
    })

    if "file_path" in result:
        print(f"✓ File downloaded with custom settings!")
        print(f"  Path: {result['file_path']}")
        print(f"  Size: {result['file_size']} bytes")
        print(f"  Type: {result['content_type']}")
        print(f"  Timeout: 60s (custom)")
        print(f"  Chunk size: 16KB (custom)")
        return True
    else:
        print(f"✗ Error: {result.get('error', 'Unknown')}")
        return False


def example_7_error_handling():
    """Example 7: Error handling demonstration"""
    print("\n" + "=" * 70)
    print("Example 7: Error Handling")
    print("=" * 70)

    config = {"name": "download_file"}
    tool = FileDownloadTool(config)

    # Try to download from invalid URL
    result = tool.run({
        "url": "https://invalid-url-that-does-not-exist.example.com/file.txt",
        "timeout": 5
    })

    if "error" in result:
        print(f"✓ Error handled correctly!")
        print(f"  Error message: {result['error']}")
        print(f"  Note: This demonstrates proper error handling")
        return True
    else:
        print(f"✗ Unexpected result: {result}")
        return False


def example_8_batch_download():
    """Example 8: Batch download multiple files"""
    print("\n" + "=" * 70)
    print("Example 8: Batch Download Multiple Files")
    print("=" * 70)

    config = {"name": "download_file"}
    tool = FileDownloadTool(config)

    # List of URLs to download
    urls = [
        ("https://jsonplaceholder.typicode.com/posts/1", "post_1.json"),
        ("https://jsonplaceholder.typicode.com/posts/2", "post_2.json"),
        ("https://jsonplaceholder.typicode.com/posts/3", "post_3.json"),
    ]

    successful = 0
    for url, filename in urls:
        result = tool.run({
            "url": url,
            "output_path": f"./downloaded_data/{filename}",
            "timeout": 30
        })

        if "file_path" in result:
            print(f"  ✓ {filename}: {result['file_size']} bytes")
            successful += 1
        else:
            print(f"  ✗ {filename}: {result.get('error', 'Failed')}")

    print(f"\n✓ Downloaded {successful}/{len(urls)} files")
    return successful == len(urls)


def cleanup_files():
    """Clean up downloaded test files"""
    print("\n" + "=" * 70)
    print("Cleaning Up Downloaded Files")
    print("=" * 70)

    files_to_remove = [
        "./downloaded_data/",
        "./example.json",
        "./all_posts.json"
    ]

    import shutil
    for path in files_to_remove:
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                    print(f"✓ Removed directory: {path}")
                else:
                    os.remove(path)
                    print(f"✓ Removed file: {path}")
            except Exception as e:
                print(f"✗ Failed to remove {path}: {e}")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("File Download Tools - Comprehensive Usage Examples")
    print("=" * 70)
    print(f"Platform: {sys.platform}")
    print(f"Working Directory: {os.getcwd()}")

    # Create output directory
    os.makedirs("./downloaded_data", exist_ok=True)

    examples = [
        ("Basic Download", example_1_basic_download),
        ("Custom Path", example_2_custom_path),
        ("Return Content", example_3_return_content),
        ("Binary Download", example_4_binary_download),
        ("Text Download", example_5_text_download),
        ("Custom Timeout", example_6_custom_timeout),
        ("Error Handling", example_7_error_handling),
        ("Batch Download", example_8_batch_download),
    ]

    results = []
    for name, func in examples:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\nTotal: {passed}/{total} examples passed")

    # Optional cleanup (comment out to keep files)
    # cleanup_files()

    print("\n" + "=" * 70)
    print("✓ Examples completed!")
    print("=" * 70)
    print("\nTip: Comment out 'cleanup_files()' to keep downloaded files")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n✗ Examples failed: {e}")
        import traceback
        traceback.print_exc()

