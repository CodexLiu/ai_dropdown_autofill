from initialize import initialize_browser
import time
from utils.scripts.verify_field_content import verify_field_content
from utils.scripts.analyze_form_fields import analyze_form_fields
from utils.scripts.visualize_element_changes import visualize_element_changes
from utils.gpt.field_state_validator import validate_field_state
import os
import tempfile


def compare_states(before, after):
    changes = []
    for key in before:
        if key in ['computedStyle', 'ariaAttributes', 'dimensions']:
            continue
        if before[key] != after[key]:
            changes.append(f"  {key}: {before[key]} -> {after[key]}")

    if changes:
        print("\nGeneral Changes:")
        for change in changes:
            print(change)


def compare_styles(before, after):
    changes = []
    for key in before:
        if before[key] != after[key]:
            changes.append(f"  {key}: {before[key]} -> {after[key]}")

    if changes:
        for change in changes:
            print(change)


def compare_aria(before, after):
    changes = []
    for key in before:
        if before[key] != after[key]:
            changes.append(f"  {key}: {before[key]} -> {after[key]}")

    if changes:
        for change in changes:
            print(change)


def process_all_fields(page, clickable_elements):
    print("\nProcessing all fields...")

    while True:
        empty_field_index = None
        for index, element in enumerate(clickable_elements):
            print(f"\nChecking field {index}: {element['label']}")

            if verify_field_content(page, element):
                print("Field already has content, skipping...")
                continue
            else:
                empty_field_index = index
                break

        if empty_field_index is None:
            print("\nNo more empty fields to process!")
            break

        print(
            f"\nProcessing empty field {empty_field_index}: {clickable_elements[empty_field_index]['label']}")

        new_elements = visualize_element_changes(
            page, clickable_elements[empty_field_index], analyze_form_fields)

        if new_elements:
            clickable_elements = new_elements
        else:
            clickable_elements = analyze_form_fields(page)

        time.sleep(0.5)

    return clickable_elements


def process_single_element(page, element_index, clickable_elements):
    try:
        if 0 <= element_index < len(clickable_elements):
            element = clickable_elements[element_index]
            print(f"\nProcessing element {element_index}: {element['label']}")

            new_elements = visualize_element_changes(
                page, element, analyze_form_fields)

            return new_elements if new_elements else analyze_form_fields(page)
        else:
            print("Invalid element number")
            return clickable_elements

    except Exception as e:
        print(f"Error processing element: {str(e)}")
        return clickable_elements


def verify_field_content(page, element):
    """Check if a field has actual selected content (not placeholder text)"""
    try:
        print("\n=== Checking Field Content ===")
        print(f"Field ID: {element['attributes']['id']}")
        print(f"Field Label: {element['label']}")
        print(f"Field Type: {element['type']}")
        print(f"Field Role: {element['attributes'].get('role')}")
        print(f"Field XPath: {element['xpath']}")
        print(f"Field Classes: {element['attributes'].get('class')}")
        print(f"Field Attributes:", element['attributes'])

        # Try built-in verification first
        field_state = page.evaluate(f'''() => {{
            function getFieldByMultipleMethods() {{
                let el;
                
                // Try by ID
                const id = "{element['attributes']['id']}";
                if (id) {{
                    el = document.getElementById(id);
                    if (el) return {{ method: 'id', element: el }};
                }}
                
                // Try by XPath
                const xpath = "{element['xpath']}";
                if (xpath) {{
                    el = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (el) return {{ method: 'xpath', element: el }};
                }}
                
                // Try by role and label
                const label = "{element['label']}";
                if (label) {{
                    el = Array.from(document.querySelectorAll('[role="combobox"], [role="listbox"], select, input'))
                        .find(e => e.getAttribute('aria-label') === label || 
                                 document.querySelector(`label[for="${{e.id}}"]`)?.textContent.includes(label));
                    if (el) return {{ method: 'role_label', element: el }};
                }}
                
                return null;
            }}

            const result = getFieldByMultipleMethods();
            if (!result) return {{ error: 'Could not find field' }};
            
            const el = result.element;
            const style = window.getComputedStyle(el);
            
            // Get parent element info
            const parent = el.parentElement;
            const parentInfo = parent ? {{
                tag: parent.tagName,
                class: parent.className,
                role: parent.getAttribute('role'),
                id: parent.id
            }} : null;
            
            // Get all possible selected values
            const selectedValue = el.querySelector('.select__single-value, .selected-value, [class*="selected"], [class*="value"]');
            const selectedOption = el.querySelector('[aria-selected="true"]');
            const selectedText = selectedValue ? selectedValue.textContent : null;
            
            return {{
                foundBy: result.method,
                value: el.value || '',
                textContent: el.textContent || '',
                innerText: el.innerText || '',
                selectedText: selectedText || '',
                ariaValue: el.getAttribute('aria-valuenow') || el.getAttribute('aria-valuetext') || '',
                selectedAriaText: selectedOption ? selectedOption.textContent : '',
                placeholder: el.getAttribute('placeholder') || '',
                isDisabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
                isReadOnly: el.readOnly || el.getAttribute('aria-readonly') === 'true',
                hasPlaceholderClass: el.classList.contains('placeholder'),
                isEmptyClass: el.classList.contains('empty'),
                visibility: style.visibility,
                display: style.display,
                computedHeight: style.height,
                ariaExpanded: el.getAttribute('aria-expanded'),
                ariaHasPopup: el.getAttribute('aria-haspopup'),
                ariaControls: el.getAttribute('aria-controls'),
                ariaOwns: el.getAttribute('aria-owns'),
                ariaDescribedby: el.getAttribute('aria-describedby'),
                classList: Array.from(el.classList).join(' '),
                tagName: el.tagName,
                parent: parentInfo,
                childElements: Array.from(el.children).map(child => ({{
                    tag: child.tagName,
                    text: child.textContent,
                    class: child.className,
                    role: child.getAttribute('role'),
                    ariaSelected: child.getAttribute('aria-selected')
                }}))
            }};
        }}''')

        if field_state:
            print("\nField State Details:")
            if 'error' in field_state:
                print(f"Error: {field_state['error']}")
                # If built-in verification fails, try image-based validation
                print("\nFalling back to image-based validation...")

                # Create a temporary file for the screenshot
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                    screenshot_path = tmp_file.name
                    # Take screenshot of the current page state
                    page.screenshot(path=screenshot_path)

                    try:
                        # Use GPT-4 Vision to validate field state
                        is_filled = validate_field_state(
                            screenshot_path, element)
                        print(
                            f"Image-based validation result: {'Filled' if is_filled else 'Empty'}")

                        # Clean up the temporary file
                        os.unlink(screenshot_path)
                        return is_filled
                    except Exception as e:
                        print(f"Error in image-based validation: {e}")
                        os.unlink(screenshot_path)
                        return False

            print(f"Found by method: {field_state.get('foundBy', 'unknown')}")
            print(f"Tag name: {field_state.get('tagName', 'unknown')}")
            print(f"Parent: {field_state.get('parent', {})}")
            print("\nField Values:")
            for key, value in field_state.items():
                if key not in ['childElements', 'parent']:
                    print(f"  {key}: '{value}'")

            print("\nChild Elements:")
            for child in field_state.get('childElements', []):
                print(
                    f"  {child['tag']}: '{child['text']}' (Role: {child['role']}, Selected: {child['ariaSelected']})")

            # Check for actual selected value
            value_fields = ['selectedText',
                            'selectedAriaText', 'value', 'ariaValue']
            for field in value_fields:
                value = field_state.get(field, '').strip()
                if value:
                    print(f"\nFound potential value in {field}: '{value}'")
                    # Check if it's not a placeholder
                    if not any(text in value.lower() for text in [
                        "select...", "all selected options have been cleared",
                        "choose an option", "no selection", "select an option"
                    ]):
                        print(f"Valid value found: '{value}'")
                        return True

            print("\nNo valid selected value found")
            # If built-in verification indicates empty, try image-based validation
            print("\nFalling back to image-based validation...")

            # Create a temporary file for the screenshot
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                screenshot_path = tmp_file.name
                # Take screenshot of the current page state
                page.screenshot(path=screenshot_path)

                try:
                    # Use GPT-4 Vision to validate field state
                    is_filled = validate_field_state(screenshot_path, element)
                    print(
                        f"Image-based validation result: {'Filled' if is_filled else 'Empty'}")

                    # Clean up the temporary file
                    os.unlink(screenshot_path)
                    return is_filled
                except Exception as e:
                    print(f"Error in image-based validation: {e}")
                    os.unlink(screenshot_path)
                    return False
        else:
            print("Could not access field state")
            # If built-in verification fails completely, try image-based validation
            print("\nFalling back to image-based validation...")

            # Create a temporary file for the screenshot
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
                screenshot_path = tmp_file.name
                # Take screenshot of the current page state
                page.screenshot(path=screenshot_path)

                try:
                    # Use GPT-4 Vision to validate field state
                    is_filled = validate_field_state(screenshot_path, element)
                    print(
                        f"Image-based validation result: {'Filled' if is_filled else 'Empty'}")

                    # Clean up the temporary file
                    os.unlink(screenshot_path)
                    return is_filled
                except Exception as e:
                    print(f"Error in image-based validation: {e}")
                    os.unlink(screenshot_path)
                    return False

    except Exception as e:
        print(f"Error in verify_field_content: {e}")
        print(f"Error type: {type(e).__name__}")
        # If any error occurs, try image-based validation as a last resort
        print("\nFalling back to image-based validation...")

        # Create a temporary file for the screenshot
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            screenshot_path = tmp_file.name
            # Take screenshot of the current page state
            page.screenshot(path=screenshot_path)

            try:
                # Use GPT-4 Vision to validate field state
                is_filled = validate_field_state(screenshot_path, element)
                print(
                    f"Image-based validation result: {'Filled' if is_filled else 'Empty'}")

                # Clean up the temporary file
                os.unlink(screenshot_path)
                return is_filled
            except Exception as e:
                print(f"Error in image-based validation: {e}")
                os.unlink(screenshot_path)
                return False


def main():
    try:
        chrome_process, playwright, browser, pages = initialize_browser()
        clickable_elements = analyze_form_fields(pages[0])

        while True:
            try:
                choice = input(
                    "\nEnter element number to visualize, 'all' to process all fields, 'r' to refresh list, or 'q' to quit: ")

                if choice.lower() == 'q':
                    break
                elif choice.lower() == 'r':
                    print("\nRefreshing list of elements...")
                    clickable_elements = analyze_form_fields(pages[0])
                elif choice.lower() == 'all':
                    print("\nProcessing all fields in sequence...")
                    clickable_elements = process_all_fields(
                        pages[0], clickable_elements)
                else:
                    element_index = int(choice)
                    clickable_elements = process_single_element(
                        pages[0], element_index, clickable_elements)

            except ValueError:
                if choice.lower() not in ['q', 'r', 'all']:
                    print(
                        "Please enter a valid number, 'all' to process all fields, 'r' to refresh, or 'q' to quit")

        input("\nPress Enter to exit...")
    except Exception as e:
        print(f"Error in main: {str(e)}")
    finally:
        browser.close()
        playwright.stop()
        chrome_process.terminate()


if __name__ == "__main__":
    main()
