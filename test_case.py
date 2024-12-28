from playwright.sync_api import sync_playwright
import time
import subprocess
import os


def initialize_browser():
    """Initialize Chrome and open multiple test URLs"""
    # Launch Chrome with remote debugging enabled
    chrome_process = subprocess.Popen([
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '--remote-debugging-port=9222',
        '--user-data-dir=/Users/codyliu/Library/Application Support/Google/Chrome',
        '--profile-directory=Profile 4'
    ])

    # Test URLs
    test_urls = [
        # Replace with your actual URLs
        # "https://job-boards.greenhouse.io/alphataraxia/jobs/4533582007?utm_source=Simplify&gh_src=Simplify",
        # "https://boards.greenhouse.io/vaticlabs/jobs/598228?utm_source=Simplify&gh_src=Simplify",
        # "https://www.verition.com/open-positions?gh_jid=4011276007?utm_source=Simplify&gh_src=Simplify",
        # "https://boards.greenhouse.io/scm/jobs/4833274?utm_source=Simplify&gh_src=Simplify",
        "https://job-boards.greenhouse.io/twitch/jobs/7777001002?utm_source=Simplify&gh_src=Simplify"
        # "https://careers.adobe.com/us/en/apply?jobSeqNo=ADOBUSR149673EXTERNALENUS&utm_campaign=google_jobs_apply&utm_source=google_jobs_apply&utm_medium=organic&step=1&stepname=personalInformation"
    ]

    # Connect to Chrome and set up initial state
    playwright = sync_playwright().start()
    browser = playwright.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]

    # Open each URL in a new tab
    pages = []
    for url in test_urls:
        page = context.new_page()
        page.goto(url)
        pages.append(page)
        print(f"Opened: {url}")

    print("\nAll test pages opened. Available pages:")
    for i, page in enumerate(pages):
        print(f"{i}: {page.url}")

    return chrome_process, playwright, browser, pages


def main():
    try:
        # Initialize browser and open test pages
        chrome_process, playwright, browser, pages = initialize_browser()

        # Keep the script running until user wants to exit
        input("\nPress Enter to exit...")

    except Exception as e:
        print(f"Error in main: {str(e)}")
        print(f"Error type: {type(e).__name__}")
    finally:
        # Clean up
        browser.close()
        playwright.stop()
        chrome_process.terminate()


if __name__ == "__main__":
    main()
