# Automated Dropdown Field Filler

A Python-based tool that demonstrates automated dropdown field filling using Playwright and GPT-4, primarily tested with Greenhouse job applications. This project showcases how to intelligently interact with dropdown fields in web forms.

## Features

- Automated detection and interaction with dropdown fields
- Smart field content analysis using GPT-4
- Support for various dropdown implementations (React-Select, standard HTML selects, custom dropdowns)
- Retry mechanism with intelligent search term generation
- Visual state validation using GPT-4 Vision

## Prerequisites

- Python 3.8+
- Google Chrome browser
- macOS (current implementation is macOS-specific, but can be adapted for other platforms)
- OpenAI API key

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd playwright_test
```

2. Install required packages:

```bash
pip install playwright openai python-dotenv
```

3. Install Playwright browsers:

```bash
playwright install
```

4. Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_api_key_here
```

## Configuration

### Browser Setup (`initialize.py`)

The `initialize.py` file handles the browser initialization and configuration. You'll need to modify this file to:

1. Set your test URLs:

```python
test_urls = [
    "https://job-boards.greenhouse.io/your-job-url",
    # Add more URLs as needed
]
```

2. Configure Chrome settings (if needed):

```python
chrome_process = subprocess.Popen([
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '--remote-debugging-port=9222',  # Default debugging port
    '--user-data-dir=/Users/YOUR_USERNAME/Library/Application Support/Google/Chrome',
    '--profile-directory=Profile 4'  # Chrome profile to use
])
```

The `initialize_browser()` function:

- Launches Chrome with remote debugging enabled
- Connects Playwright to the running Chrome instance
- Opens each URL from your test_urls list in a new tab
- Returns the necessary browser control objects

This approach allows the script to:

- Use your existing Chrome profile (cookies, saved passwords, etc.)
- Handle multiple job applications simultaneously
- Maintain browser state between runs

## Usage

1. Configure your URLs in `initialize.py` as described above.

2. Run the main script:

```bash
python run_dropdown_fill.py
```

3. Interactive Commands:

- Enter a number to process a specific dropdown field
- Enter 'all' to process all fields sequentially
- Enter 'r' to refresh the list of fields
- Enter 'q' to quit

## Project Structure

- `run_dropdown_fill.py`: Main execution script
- `initialize.py`: Browser initialization and setup
- `utils/`
  - `gpt/`: GPT-4 integration modules
  - `scripts/`: Core functionality scripts

## Limitations

1. **URL Structure**: Currently optimized for Greenhouse job board URLs, but can be adapted for other platforms
2. **Browser Support**: Currently configured for Chrome on macOS
3. **Field Detection**: Works best with standard dropdown implementations and common frameworks like React-Select
4. **File Structure**: Current implementation assumes a specific project structure for demonstration purposes

## Extending the Project

To make this tool universally cover job applications:

1. Implement additional dropdown detection patterns
2. Add support for different job board platforms
3. Create platform-specific handlers
4. Enhance the field analysis logic
5. Add cross-platform browser support

## Contributing

Feel free to fork this project and adapt it for your needs. This is a demonstration of how automated form filling could work, and there's plenty of room for enhancement and generalization.

## License

MIT

## Disclaimer

This tool is for demonstration purposes only. Make sure to comply with website terms of service and robot policies when implementing automated form filling.
