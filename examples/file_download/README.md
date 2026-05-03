# File Download Tools - Usage Examples

## Overview

The File Download Tools provide curl-like functionality for downloading files from URLs with full cross-platform support (Windows, Mac, Linux).

## Available Tools

### 1. FileDownloadTool
**Most flexible tool** - Downloads any type of file, can save to disk or return content directly.

**Features:**
- Save to specified path or temporary directory
- Return content directly without saving
- Configure chunk size and timeout
- Automatic redirect following
- Binary and text file support

### 2. BinaryDownloadTool
**Optimized for large files** - Designed for downloading images, videos, executables, and other binary files.

**Features:**
- Large chunk sizes (1MB default) for better performance
- Optimized memory usage
- Required output path specification
- Best for files > 100KB

### 3. TextDownloadTool
**Text content optimized** - Downloads and returns text content with automatic encoding detection.

**Features:**
- Returns content as string directly
- Automatic encoding detection
- Manual encoding specification supported
- Best for text files, JSON, HTML, etc.

## Quick Start

### Basic File Download

```python
from tooluniverse.file_download_tool import FileDownloadTool

# Create tool
config = {"name": "download_file"}
tool = FileDownloadTool(config)

# Download file
result = tool.run({
    "url": "https://example.com/file.txt",
    "output_path": "./downloaded_file.txt"
})

print(f"File saved to: {result['file_path']}")
print(f"Size: {result['file_size']} bytes")
```

### Download Large Files

```python
from tooluniverse.file_download_tool import BinaryDownloadTool

config = {"name": "download_binary"}
tool = BinaryDownloadTool(config)

result = tool.run({
    "url": "https://example.com/video.mp4",
    "output_path": "./video.mp4",
    "chunk_size": 1024 * 1024,  # 1MB chunks
    "timeout": 300  # 5 minutes timeout
})

print(f"Downloaded {result['size']} bytes")
```

### Get Content Without Saving

```python
from tooluniverse.file_download_tool import FileDownloadTool

config = {"name": "download_file"}
tool = FileDownloadTool(config)

result = tool.run({
    "url": "https://api.example.com/data.json",
    "return_content": True
})

# Use content directly
import json
data = json.loads(result['content'])
```

## Examples in This Directory

- **`use_download.py`** - Comprehensive examples using all three download tools
- **`test_real_file_download.py`** - Tests with real files from the internet

## Use Cases

### 1. Download Data Files

```python
# Download CSV data
tool = FileDownloadTool(config)
result = tool.run({
    "url": "https://data.gov/api/file.csv",
    "output_path": "./data.csv"
})
```

### 2. Process API Responses

```python
# Download JSON and parse
result = tool.run({
    "url": "https://api.example.com/data",
    "return_content": True
})
data = json.loads(result['content'])
```

### 3. Download Media Files

```python
# Download images
binary_tool = BinaryDownloadTool(config)
result = binary_tool.run({
    "url": "https://example.com/image.jpg",
    "output_path": "./image.jpg"
})
```

### 4. Fetch Remote Configuration

```python
# Download configuration files
text_tool = TextDownloadTool(config)
result = text_tool.run({
    "url": "https://example.com/config.yaml"
})
config = yaml.safe_load(result['content'])
```

## Features

### Cross-Platform Support
- ✅ Windows paths: `C:\Users\user\file.txt`
- ✅ Mac/Linux paths: `/home/user/file.txt`
- ✅ Environment variables: `$HOME/file.txt` → `/Users/user/file.txt`
- ✅ User directory: `~/file.txt` → `/Users/user/file.txt`

### Automatic Path Handling
The tool automatically:
- Expands `~` to user home directory
- Expands environment variables
- Converts relative paths to absolute
- Creates parent directories if needed

### Error Handling
All tools return error information:

```python
result = tool.run({"url": "invalid-url"})

if "error" in result:
    print(f"Error: {result['error']}")
else:
    print(f"Success: {result['file_path']}")
```

## Parameters Reference

### FileDownloadTool

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | ✅ | - | URL to download |
| `output_path` | string | ❌ | temp dir | Where to save |
| `timeout` | int | ❌ | 30 | Timeout in seconds |
| `return_content` | bool | ❌ | False | Return content directly |
| `chunk_size` | int | ❌ | 8192 | Download chunk size |
| `follow_redirects` | bool | ❌ | True | Follow redirects |

### BinaryDownloadTool

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | ✅ | - | URL to download |
| `output_path` | string | ✅ | - | Where to save |
| `timeout` | int | ❌ | 30 | Timeout in seconds |
| `chunk_size` | int | ❌ | 1048576 | Chunk size (1MB) |

### TextDownloadTool

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string | ✅ | - | URL to download |
| `timeout` | int | ❌ | 30 | Timeout in seconds |
| `encoding` | string | ❌ | auto | Text encoding |

## Running Examples

```bash
# Run comprehensive examples
python examples/file_download/use_download.py

# Run real file download tests
python examples/test_real_file_download.py
```

## Comparison with Other URL Tools

| Feature | FileDownloadTool | URLToPDFTextTool | URLHTMLTagTool |
|---------|------------------|------------------|----------------|
| Save to disk | ✅ | ❌ | ❌ |
| Binary files | ✅ | ❌ | ❌ |
| Browser rendering | ❌ | ✅ | ❌ |
| Text extraction | ✅ | ✅ | ✅ |
| Large files | ✅ | ❌ | ❌ |

## Tips

1. **For large files**: Use `BinaryDownloadTool` with larger chunk sizes
2. **For JSON/API data**: Use `return_content=True` with `FileDownloadTool`
3. **For text files**: Use `TextDownloadTool` for better encoding handling
4. **Set appropriate timeouts**: Larger files need longer timeouts
5. **Use temporary directory**: Let the tool handle temp files automatically

## Dependencies

- `requests` - For HTTP requests

## More Information

- Full documentation: `docs/file_download_tool_usage.md`
- Test results: `REAL_DOWNLOAD_TEST_RESULTS.md`
- Implementation: `src/tooluniverse/file_download_tool.py`

