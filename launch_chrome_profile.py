from playwright.sync_api import sync_playwright
import time
import subprocess
import os
import pyautogui
from openai import OpenAI
from dotenv import load_dotenv
from automation_script import print_clickable_elements, print_form_elements

# Load environment variables
load_dotenv()

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    raise ValueError(
        "No OpenAI API key found. Make sure OPENAI_API_KEY is set in your .env file")
client = OpenAI(api_key=api_key)

# Add safety delay for mouse movements
pyautogui.PAUSE = 0.5  # Add delay between PyAutoGUI commands
pyautogui.FAILSAFE = True  # Move mouse to upper-left to abort


def initialize_browser():
    """Initialize Chrome and navigate to the matches page"""
    # Launch Chrome normally with remote debugging enabled
    chrome_process = subprocess.Popen([
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '--remote-debugging-port=9222',
        '--user-data-dir=/Users/codyliu/Library/Application Support/Google/Chrome',
        '--profile-directory=Profile 4'
    ])

    # Connect to Chrome and set up initial state
    playwright = sync_playwright().start()
    browser = playwright.chromium.connect_over_cdp("http://localhost:9222")
    context = browser.contexts[0]
    page = context.new_page()

    # Navigate and perform initial setup
    page.goto("https://simplify.jobs/dashboard")
    print("Connected to existing Chrome browser...")
    time.sleep(2)

    # Handle sign in if needed
    sign_in_button = page.get_by_role("button", name="Sign in", exact=True)
    if sign_in_button.is_visible():
        sign_in_button.click()
        time.sleep(2)
        print("Clicked sign in button")

    # Navigate to matches
    matches_link = page.get_by_role("link", name="Matches", exact=True).first
    matches_link.click()
    print("Clicked matches link")
    time.sleep(5)

    return chrome_process, playwright, browser, page


def click_simplify_extension():
    """Click the Simplify extension buttons"""
    try:
        print("Starting extension click sequence...")
        time.sleep(5)
        # Get current mouse position for debuggingxr
        current_x, current_y = pyautogui.position()
        print(f"Current mouse position: ({current_x}, {current_y})")

        # Wait for extension to appear
        time.sleep(2)

        # Move mouse slowly to target (added duration for visibility)
        print("Moving mouse to target position...")
        pyautogui.moveTo(1237, 364, duration=0.2)

        # Get position after move for verification
        after_move_x, after_move_y = pyautogui.position()
        print(f"Mouse position after move: ({after_move_x}, {after_move_y})")

        # Click and verify
        pyautogui.click()
        print("Clicked at position")

        # Get screen size for debugging
        screen_width, screen_height = pyautogui.size()
        print(f"Screen size: {screen_width}x{screen_height}")

        time.sleep(10)  # Wait for next button if needed

    except Exception as e:
        print(f"Error clicking extension: {e}")
        print(f"Error type: {type(e).__name__}")


def get_button_choice(clickable_elements):
    """Use GPT-3.5 to determine which button to click"""
    try:
        # Format the clickable elements into a clear message
        message = "Given these clickable elements on a job application page, return ONLY the exact text of the button that should be clicked to submit the application. Return ONLY the button text, nothing else.\n\nClickable elements:\n"
        message += clickable_elements

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": message}
            ],
            temperature=0.1  # Low temperature for consistent responses
        )

        button_text = response.choices[0].message.content.strip()
        print(f"AI suggests clicking button with text: {button_text}")
        return button_text

    except Exception as e:
        print(f"Error getting AI button choice: {e}")
        return None


def click_ai_selected_button(page, button_text):
    """Click the button selected by AI"""
    try:
        button = page.get_by_role("button", name=button_text, exact=True).first
        if button and button.is_visible():
            button.click()
            print(f"Successfully clicked '{button_text}' button")
            return True
    except Exception as e:
        print(f"Error clicking button: {e}")
    return False


def get_field_response(field_info):
    """Get optimal response for a form field using GPT"""
    try:
        message = f"""For a job application, provide the BEST POSSIBLE ANSWER for this field. 
        Return ONLY the answer, no explanation.
        
        Field details:
        Label/Question: {field_info['label']}
        Type: {field_info['type']}
        Options: {field_info['options'] if 'options' in field_info else 'None'}
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": message}],
            temperature=0.1
        )

        answer = response.choices[0].message.content.strip()
        print(f"AI suggests answer for {field_info['label']}: {answer}")
        return answer

    except Exception as e:
        print(f"Error getting AI field response: {e}")
        return None


def handle_empty_fields(page):
    """Find and fill empty required fields"""
    try:
        # Get all form elements
        form_elements = page.evaluate('''() => {
            function getFieldDetails(el) {
                return {
                    type: el.type || el.tagName.toLowerCase(),
                    required: el.required || false,
                    value: el.value || '',
                    name: el.name || '',
                    label: (el.labels && el.labels[0] ? el.labels[0].textContent : '') || 
                           el.getAttribute('aria-label') || 
                           el.getAttribute('placeholder') || 
                           el.name,
                    options: el.tagName === 'SELECT' ? 
                        Array.from(el.options).map(opt => opt.text) : null,
                    isVisible: el.offsetParent !== null,
                    isEnabled: !el.disabled
                };
            }

            const selectors = [
                'input:not([type="hidden"])',
                'select',
                'textarea',
                '[role="combobox"]',
                '[role="listbox"]',
                'input[type="checkbox"]'
            ];

            return Array.from(document.querySelectorAll(selectors.join(',')))
                .filter(el => el.required && !el.value && el.offsetParent !== null)
                .map(getFieldDetails);
        }''')

        print("\nChecking for empty required fields...")
        for field in form_elements:
            if not field['isEnabled'] or not field['isVisible']:
                continue

            print(f"\nHandling empty field: {field['label']}")

            if field['type'] in ['text', 'textarea', 'email', 'tel', 'url']:
                # Get AI response for text fields
                response = get_field_response(field)
                if response:
                    # Fill the field using appropriate selector
                    selector = f'[name="{field["name"]}"]' if field['name'] else f'[aria-label="{field["label"]}"]'
                    page.fill(selector, response)
                    print(f"Filled text field: {field['label']}")

            elif field['type'] == 'select' or field['type'] == 'combobox':
                # Get AI choice for dropdown
                field['context'] = "Choose the option that would make the strongest candidate"
                choice = get_field_response(field)
                if choice and choice in field['options']:
                    page.select_option(
                        f'select[name="{field["name"]}"]', choice)
                    print(f"Selected dropdown option: {choice}")

            elif field['type'] == 'checkbox':
                # Get AI decision for checkbox
                field['context'] = "Should this box be checked for the strongest application? Return only YES or NO"
                decision = get_field_response(field)
                if decision and decision.upper() == 'YES':
                    page.check(f'input[name="{field["name"]}"]')
                    print(f"Checked checkbox: {field['label']}")

            time.sleep(0.5)  # Brief pause between fields

    except Exception as e:
        print(f"Error handling empty fields: {e}")
        print(f"Error type: {type(e).__name__}")


def click_next_job_button(page):
    """Find and click the next job button"""
    print("\nLooking for next job button...")
    button = page.locator(
        'button.hidden.size-14.items-center.justify-center.rounded-full.bg-white.shadow').first
    if button.is_visible():
        print("Found next job button, clicking...")
        button.click()
        print("Clicked next job button")
        time.sleep(0.5)  # Reduced wait from 2 seconds to 1 second
        return True
    else:
        print("Next job button not found or not visible")
        return False


def find_and_click_submit(page):
    """Find and click the submit button using multiple strategies"""
    print("\nLooking for submit button...")

    # Print all visible buttons for debugging
    elements = page.evaluate('''() => {
        function getElementDetails(el) {
            return {
                tag: el.tagName.toLowerCase(),
                text: el.textContent.trim(),
                type: el.type || '',
                role: el.getAttribute('role'),
                id: el.id,
                class: el.className,
                isVisible: el.offsetParent !== null,
                isEnabled: !el.disabled
            };
        }

        const elements = document.querySelectorAll('button, input[type="submit"], [role="button"]');
        return Array.from(elements)
            .filter(el => {
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0' &&
                       el.offsetParent !== null;
            })
            .map(getElementDetails);
    }''')

    # Print visible buttons for debugging
    print("\n=== All Clickable Elements ===")
    for el in elements:
        if el.get('text'):
            print(
                f"Button: {el.get('text', '')} ({el.get('type', 'none')}, {el.get('class', 'none')})")

    submit_strategies = [
        # Text-based selectors
        lambda: page.get_by_role(
            "button", name="Submit Application", exact=True).click(),
        lambda: page.get_by_role(
            "button", name="Submit application", exact=True).click(),
        lambda: page.get_by_role("button", name="Submit", exact=True).click()
    ]

    for i, strategy in enumerate(submit_strategies):
        try:
            print(f"\nTrying submit strategy {i+1}...")
            strategy()
            print(f"Successfully clicked submit button with strategy {i+1}")
            # Reduced wait time to 0.5 seconds after successful click
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"Strategy {i+1} failed: {str(e)}")
            time.sleep(0.5)  # Added 0.5 second wait between failed attempts
            continue

    print("\nFailed to find and click submit button with all strategies")
    return False


def check_page_stuck(page, timeout=10):
    """Check if page is stuck by monitoring URL changes"""
    print(
        f"\nStarting {timeout} second countdown to check if page is stuck...")
    initial_url = page.url

    for i in range(timeout, 0, -1):
        print(f"Checking if page is stuck... {i} seconds remaining")
        if page.url != initial_url:
            print("Page URL changed, not stuck")
            return False
        time.sleep(1)

    print("Page appears to be stuck (URL hasn't changed)")
    return True


def apply_for_jobs(page, timeout=300):
    """Loop through jobs and click apply buttons"""
    print("\nStarting job application process...")
    start_time = time.time()

    # More specific selector for the Apply button - only get the first visible one
    apply_button = page.locator('button:has-text("Apply")').first

    if apply_button and apply_button.is_visible():
        print("Found Apply button, clicking...")

        try:
            # Wait for any existing pages to settle
            time.sleep(1)

            # Count existing pages before clicking
            initial_pages = len(page.context.pages)
            print(f"Number of pages before clicking Apply: {initial_pages}")

            # Click with expect_page to handle the new tab
            with page.context.expect_page(timeout=10000) as new_page_info:
                apply_button.click(timeout=5000)
                print("Successfully clicked Apply button")

            # Get the new page and verify it's actually new
            application_page = new_page_info.value
            current_pages = len(page.context.pages)
            print(f"Number of pages after clicking Apply: {current_pages}")

            if current_pages > initial_pages + 1:
                print("Warning: Multiple tabs were opened. Closing excess tabs...")
                # Keep only the original page and the newest application page
                for p in page.context.pages:
                    if p != page and p != application_page:
                        p.close()

            print("New application page opened:", application_page.url)

            # Check if elapsed time exceeds timeout
            def check_timeout():
                if time.time() - start_time > timeout:
                    print(
                        f"\nTimeout reached after {timeout} seconds. Moving to next job...")
                    application_page.close()
                    return True
                return False

            # Check if it's a Workday URL
            if "workday" in application_page.url.lower():
                print("Workday application detected, skipping...")
                application_page.close()
                print("Closed Workday application tab")

                # Try to move to next job
                if click_next_job_button(page):
                    print("Moving to next job...")
                    time.sleep(5)  # Wait for next job to load
                    return True  # Continue the loop
                else:
                    print(
                        "Could not find next job button, checking for more matches...")
                    view_more_button = page.get_by_role("button").filter(
                        has_text="View more matches").first
                    if view_more_button and view_more_button.is_visible():
                        view_more_button.click()
                        print("Clicked View more matches button")
                        time.sleep(5)  # Wait for new matches to load
                        return True
                    else:
                        print("No more matches button found either, stopping...")
                        return False

            # Wait for the page to load
            time.sleep(5)
            if check_timeout():
                return True

            # Click the Simplify extension
            click_simplify_extension()
            print("Clicked Simplify extension")

            # Wait for Simplify to fill the form
            time.sleep(10)
            if check_timeout():
                return True

            # Read resume text
            with open('info.txt', 'r') as file:
                resume_text = file.read()

            # Fill any remaining empty fields
            print("\nFilling remaining empty fields...")
            print_and_fill_form_fields(application_page, resume_text)
            if check_timeout():
                return True

            # Try to find and click the submit button
            print("\nAttempting to click submit button...")
            submitted = find_and_click_submit(application_page)

            # Check if page is stuck after submission
            if submitted:
                if check_timeout():
                    return True
                print("Submit button clicked, monitoring for stuck page...")
                if check_page_stuck(application_page):
                    print("Application appears stuck, closing tab and moving on...")
                    application_page.close()
                    print("Closed stuck application tab")
                else:
                    print("Application completed successfully")
                    application_page.close()
                    print("Closed application tab")

            # Click the next job button
            if click_next_job_button(page):
                print("Moving to next job...")
                time.sleep(5)  # Wait for next job to load
            else:
                print("Could not find next job button, checking for more matches...")
                view_more_button = page.get_by_role("button").filter(
                    has_text="View more matches").first
                if view_more_button and view_more_button.is_visible():
                    view_more_button.click()
                    print("Clicked View more matches button")
                    time.sleep(5)  # Wait for new matches to load
                    return True
                else:
                    print("No more matches button found either, stopping...")
                    return False

        except Exception as e:
            print(f"Error during application process: {e}")
            print(f"Error type: {type(e).__name__}")
            return False

    else:
        print("No Apply button found")
        # Try to click next job button
        if click_next_job_button(page):
            print("Moving to next job...")
            time.sleep(5)
        else:
            print("Could not find next job button, checking for more matches...")
            view_more_button = page.get_by_role("button").filter(
                has_text="View more matches").first
            if view_more_button and view_more_button.is_visible():
                view_more_button.click()
                print("Clicked View more matches button")
                time.sleep(5)  # Wait for new matches to load
                return True
            else:
                print("No more matches button found either, stopping...")
                return False

    return True  # Continue the loop


def main():
    # Initialize everything
    chrome_process, playwright, browser, page = initialize_browser()
    time.sleep(5)

    try:
        # Keep applying to jobs until we can't find the next button
        while True:
            if not apply_for_jobs(page):
                print("No more jobs to apply to or error occurred. Stopping...")
                break
            time.sleep(2)  # Brief pause between iterations

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Clean up
        browser.close()
        playwright.stop()
        chrome_process.terminate()


if __name__ == "__main__":
    main()
