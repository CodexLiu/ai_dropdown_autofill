import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import time


def print_clickable_elements(page, return_text=False):
    """Print all clickable elements and optionally return as text"""
    output_text = "\n=== All Clickable Elements ===\n"

    clickable_elements = page.evaluate('''() => {
        const elements = document.querySelectorAll('a, button, [role="button"], [type="submit"], [type="button"], [onclick], .clickable');
        return Array.from(elements).map(el => ({
            tag: el.tagName.toLowerCase(),
            text: el.innerText.trim(),
            href: el.href,
            role: el.getAttribute('role'),
            id: el.id,
            class: el.className,
            type: el.type,
            isVisible: el.offsetParent !== null,
            ariaLabel: el.getAttribute('aria-label')
        }));
    }''')

    for i, element in enumerate(clickable_elements, 1):
        if element['text'] or element['ariaLabel']:
            element_text = f"\n{i}. Clickable Element:"
            element_text += f"\n   Type: {element['tag']}"
            element_text += f"\n   Text: {element['text']}"
            if element['href']:
                element_text += f"\n   Href: {element['href']}"
            if element['ariaLabel']:
                element_text += f"\n   Aria Label: {element['ariaLabel']}"
            if element['id']:
                element_text += f"\n   ID: {element['id']}"
            element_text += f"\n   Visible: {element['isVisible']}"

            output_text += element_text
            print(element_text)

    if return_text:
        return output_text


def print_form_elements(page):
    """Print all form-related elements and their details"""
    print("\n=== Form Elements Found ===")

    form_elements = page.evaluate('''() => {
        function getElementDetails(el) {
            return {
                tag: el.tagName.toLowerCase(),
                type: el.type || null,
                name: el.name || null,
                id: el.id || null,
                placeholder: el.placeholder || null,
                value: el.value || null,
                required: el.required || false,
                class: el.className,
                isVisible: el.offsetParent !== null,
                label: el.labels && el.labels[0] ? el.labels[0].textContent.trim() : null,
                ariaLabel: el.getAttribute('aria-label'),
                options: el.tagName === 'SELECT' ? Array.from(el.options).map(opt => opt.text) : null
            };
        }
        
        // Get all form-related elements
        const selectors = [
            'input',
            'select',
            'textarea',
            'button',
            '[role="combobox"]',
            '[role="listbox"]',
            '[type="file"]',
            '[contenteditable="true"]'
        ];
        
        const elements = document.querySelectorAll(selectors.join(','));
        return Array.from(elements).map(getElementDetails);
    }''')

    # Group elements by type for better readability
    categories = {
        'Input Fields': ['text', 'email', 'tel', 'number', 'url'],
        'Dropdowns': ['select', 'combobox', 'listbox'],
        'File Uploads': ['file'],
        'Text Areas': ['textarea'],
        'Buttons': ['button', 'submit'],
        'Other Fields': []
    }

    for i, element in enumerate(form_elements, 1):
        # Skip hidden elements
        if not element['isVisible']:
            continue

        print(f"\n{i}. Element Details:")
        print(
            f"   Type: {element['tag']}{' (' + element['type'] + ')' if element['type'] else ''}")

        if element['label'] or element['ariaLabel']:
            print(f"   Label: {element['label'] or element['ariaLabel']}")

        if element['placeholder']:
            print(f"   Placeholder: {element['placeholder']}")

        if element['id']:
            print(f"   ID: {element['id']}")

        if element['name']:
            print(f"   Name: {element['name']}")

        if element['required']:
            print("   Required: Yes")

        # Print dropdown options if it's a select element
        if element['options']:
            print("   Options:")
            for opt in element['options']:
                print(f"    - {opt}")

        # Print any current value
        if element['value']:
            print(f"   Current Value: {element['value']}")


def initialize_browser():
    """Initialize browser and handle login process"""
    # Load environment variables
    load_dotenv()
    email = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')

    # Setup playwright and browser
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(channel="chrome", headless=False)
    page = browser.new_page()

    # Login process
    page.goto("https://simplify.jobs/")
    login_link = page.get_by_role("link", name="Log In")
    login_link.click()

    time.sleep(2)

    page.get_by_placeholder("Email").fill(email)
    page.get_by_placeholder("Password").fill(password)
    page.get_by_role("button", name="Sign in", exact=True).click()

    # Wait for login to complete
    time.sleep(10)

    return playwright, browser, page


def apply_for_jobs(page):
    """Loop through jobs and click apply buttons"""
    print("\nStarting job application process...")

    # Find all apply buttons
    apply_buttons = page.get_by_role("button", name="Apply", exact=True).all()
    print(f"Found {len(apply_buttons)} apply buttons")

    for i, button in enumerate(apply_buttons, 1):
        try:
            print(f"\nAttempting to apply for job {i}...")
            # Check if button is visible and clickable
            if button.is_visible():
                button.click()
                print("Successfully clicked Apply button")
                # Wait for application process/new page
                time.sleep(5)

                # Look for and click "Proceed anyway" button if present
                proceed_button = page.get_by_role(
                    "button", name="Proceed anyway", exact=True)
                if proceed_button.is_visible():
                    proceed_button.click()
                    print("Clicked 'Proceed anyway' button")
                    time.sleep(2)

                time.sleep(10)
                print_form_elements(page)

            else:
                print("Apply button not visible, skipping...")

            time.sleep(2)  # Brief pause between applications

        except Exception as e:
            print(f"Error applying for job {i}: {e}")
            continue


def main():
    # Initialize browser and get logged in page
    playwright, browser, page = initialize_browser()

    # Click on the Matches link - using exact match and more specific selector
    matches_link = page.get_by_role(
        "link", name="Matches", exact=True).first
    matches_link.click()
    time.sleep(5)

    # Start the job application loop
    apply_for_jobs(page)

    # Keep browser open briefly to see results
    time.sleep(10)

    # finally:
    # browser.close()
    # playwright.stop()


if __name__ == "__main__":
    main()
