from playwright.sync_api import sync_playwright
from test_case import initialize_browser
from gpt_dropdown_utils import get_dropdown_suggestion, get_best_option_number, models
import time
from datetime import datetime

# need was click successful function
# two types of drop dwon clicks possible one is into the textbox and the other is into the dropdown


def analyze_form_fields(page):
    """Analyze form fields and store clickable elements"""
    print(f"\n{'='*50}")
    print(f"Analyzing page: {page.url}")
    print(f"{'='*50}")

    # Get all form fields with detailed information
    form_fields = page.evaluate('''() => {
        function getFieldDetails(el) {
            // Get label through multiple methods
            const getLabel = (el) => {
                // Check explicit label
                if (el.id) {
                    const explicitLabel = document.querySelector(`label[for="${el.id}"]`);
                    if (explicitLabel) return explicitLabel.textContent.trim();
                }
                
                // Check aria-label
                if (el.getAttribute('aria-label')) 
                    return el.getAttribute('aria-label').trim();
                
                // Check parent label
                let parent = el.parentElement;
                while (parent && parent !== document.body) {
                    if (parent.tagName === 'LABEL') 
                        return parent.textContent.trim();
                    const labelChild = parent.querySelector('label');
                    if (labelChild) 
                        return labelChild.textContent.trim();
                    parent = parent.parentElement;
                }
                
                // Check for preceding text that might be a label
                const prevSibling = el.previousSibling;
                if (prevSibling && prevSibling.textContent) {
                    return prevSibling.textContent.trim();
                }
                
                return el.placeholder || el.name || '';
            };

            // Get current value and check if empty
            const getValue = (el) => {
                if (el.tagName === 'SELECT') return el.value;
                if (el.type === 'checkbox') return el.checked;
                return el.value || '';
            };

            // Get dropdown options if applicable
            const getOptions = (el) => {
                let options = [];
                
                // Standard select element
                if (el.tagName === 'SELECT') {
                    options = Array.from(el.options).map(opt => opt.text);
                }
                
                // React/Material-UI style dropdown
                if (el.getAttribute('role') === 'combobox' || 
                    el.getAttribute('role') === 'listbox' ||
                    el.className.includes('select') ||
                    el.className.includes('dropdown')) {
                    const listbox = document.querySelector(`[role="listbox"][id="${el.getAttribute('aria-controls')}"]`);
                    if (listbox) {
                        options = Array.from(listbox.querySelectorAll('[role="option"]'))
                            .map(opt => opt.textContent.trim());
                    }
                }
                
                return options;
            };

            // Get element's XPath
            const getXPath = (el) => {
                const parts = [];
                while (el && el.nodeType === Node.ELEMENT_NODE) {
                    let idx = 0;
                    let sibling = el.previousSibling;
                    while (sibling) {
                        if (sibling.nodeType === Node.ELEMENT_NODE && sibling.tagName === el.tagName) {
                            idx++;
                        }
                        sibling = sibling.previousSibling;
                    }
                    const position = idx ? `[${idx + 1}]` : '';
                    parts.unshift(el.tagName.toLowerCase() + position);
                    el = el.parentNode;
                }
                return '/' + parts.join('/');
            };

            // Determine field type with enhanced detection
            const getFieldType = (el) => {
                if (el.tagName === 'SELECT' || 
                    el.getAttribute('role') === 'combobox' || 
                    el.getAttribute('role') === 'listbox' ||
                    el.className.includes('select') ||
                    el.className.includes('dropdown')) {
                    return 'dropdown';
                }
                if (el.tagName === 'TEXTAREA' || 
                    (el.getAttribute('role') === 'textbox' && 
                     el.getAttribute('aria-multiline') === 'true')) {
                    return 'textarea';
                }
                return el.type || 'text';
            };

            const fieldType = getFieldType(el);
            const value = getValue(el);
            const label = getLabel(el);
            const options = getOptions(el);

            return {
                type: fieldType,
                label: label,
                value: value,
                isEmpty: !value,
                isRequired: el.required || el.getAttribute('aria-required') === 'true',
                isVisible: el.offsetParent !== null,
                isEnabled: !el.disabled,
                options: options,
                xpath: getXPath(el),
                attributes: {
                    id: el.id,
                    name: el.name,
                    class: el.className,
                    role: el.getAttribute('role'),
                    'aria-label': el.getAttribute('aria-label'),
                    'aria-controls': el.getAttribute('aria-controls'),
                    placeholder: el.placeholder
                }
            };
        }

        // Comprehensive selector list to catch all possible form fields
        const selectors = [
            // Standard form elements
            'input:not([type="hidden"])',
            'select',
            'textarea',
            
            // ARIA roles
            '[role="textbox"]',
            '[role="combobox"]',
            '[role="listbox"]',
            '[role="searchbox"]',
            '[role="button"]',
            
            // Common framework-specific selectors
            '.MuiSelect-root',
            '.react-select',
            '.form-control',
            '[class*="input"]',
            '[class*="select"]',
            '[class*="dropdown"]',
            '[class*="textbox"]',
            '[class*="textarea"]',
            '[class*="button"]',
            
            // Editable elements
            '[contenteditable="true"]',
            
            // Custom components that might be inputs
            '[class*="form-field"]',
            '[class*="form-input"]',
            '[class*="form-control"]'
        ];

        return Array.from(document.querySelectorAll(selectors.join(',')))
            .filter(el => {
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0' &&
                       el.offsetParent !== null;
            })
            .map(getFieldDetails);
    }''')

    # Store all fields with their indices
    clickable_elements = []
    current_index = 0

    # Group fields by type
    print("\n=== Form Field Analysis ===")

    # Handle dropdowns with duplicate removal
    print("\nDropdowns:")
    seen_labels = set()
    for field in form_fields:
        if field['type'] == 'dropdown':
            label = field['label']
            if label not in seen_labels:
                seen_labels.add(label)
                print(f"\n[{current_index}] Label: {label}")
                print(f"    Empty: {field['isEmpty']}")
                print(f"    Required: {field['isRequired']}")
                if field['options']:
                    print(f"    Options: {field['options']}")
                clickable_elements.append(field)
                current_index += 1
            else:
                print(f"    Skipping duplicate dropdown with label: {label}")

    print("\nText Fields:")
    for field in form_fields:
        if field['type'] in ['text', 'email', 'tel', 'url', 'search']:
            print(f"\n[{current_index}] Label: {field['label']}")
            print(f"    Type: {field['type']}")
            print(f"    Empty: {field['isEmpty']}")
            print(f"    Required: {field['isRequired']}")
            clickable_elements.append(field)
            current_index += 1

    print("\nTextareas:")
    for field in form_fields:
        if field['type'] == 'textarea':
            print(f"\n[{current_index}] Label: {field['label']}")
            print(f"    Empty: {field['isEmpty']}")
            print(f"    Required: {field['isRequired']}")
            clickable_elements.append(field)
            current_index += 1

    print("\nOther Fields:")
    for field in form_fields:
        if field['type'] not in ['dropdown', 'text', 'email', 'tel', 'url', 'search', 'textarea']:
            print(f"\n[{current_index}] Type: {field['type']}")
            print(f"    Label: {field['label']}")
            print(f"    Empty: {field['isEmpty']}")
            print(f"    Required: {field['isRequired']}")
            clickable_elements.append(field)
            current_index += 1

    return clickable_elements


def get_current_elements(page):
    """Get all current visible elements on the page"""
    return page.evaluate('''() => {
        return Array.from(document.querySelectorAll('*'))
            .filter(el => {
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0' &&
                       el.offsetParent !== null;
            })
            .map(el => ({
                tag: el.tagName.toLowerCase(),
                text: el.textContent.trim(),
                class: el.className,
                role: el.getAttribute('role'),
                id: el.id,
                type: el.type || '',
                'aria-expanded': el.getAttribute('aria-expanded'),
                'aria-controls': el.getAttribute('aria-controls')
            }));
    }''')


def compare_elements(before_elements, after_elements):
    """Compare elements and return newly added ones"""
    # Create unique identifiers for elements
    def element_identifier(el):
        return f"{el['tag']}_{el['id']}_{el['class']}_{el['role']}_{el['text']}"

    before_ids = set(element_identifier(el) for el in before_elements)
    new_elements = [
        el for el in after_elements if element_identifier(el) not in before_ids]

    return new_elements


def click_element(page, element):
    """Attempt to click an element using multiple strategies and track new elements"""
    try:
        # Get elements before clicking
        before_elements = get_current_elements(page)

        # Try clicking by ID
        clicked = False
        if element['attributes']['id']:
            try:
                page.click(f"#{element['attributes']['id']}")
                print(f"Clicked element by ID: {element['attributes']['id']}")
                clicked = True
            except:
                pass

        if not clicked and element['xpath']:
            try:
                page.click(f"xpath={element['xpath']}")
                print(f"Clicked element by XPath")
                clicked = True
            except:
                pass

        if not clicked and element['attributes']['role'] and element['label']:
            try:
                page.get_by_role(element['attributes']
                                 ['role'], name=element['label']).click()
                print(f"Clicked element by role and label")
                clicked = True
            except:
                pass

        if not clicked and element['attributes']['class']:
            try:
                page.click(f".{element['attributes']['class'].split()[0]}")
                print(f"Clicked element by class")
                clicked = True
            except:
                pass

        if clicked:
            # Wait for potential animations/changes
            time.sleep(0.5)

            # Get elements after clicking
            after_elements = get_current_elements(page)

            # Compare and print new elements
            new_elements = compare_elements(before_elements, after_elements)

            if new_elements:
                print("\nNewly added elements after click:")
                for i, el in enumerate(new_elements):
                    print(f"\n[{i}] New Element:")
                    if el['text']:
                        print(f"    Text: {el['text']}")
                    if el['role']:
                        print(f"    Role: {el['role']}")
                    if el['type']:
                        print(f"    Type: {el['type']}")
                    if el['class']:
                        print(f"    Class: {el['class']}")
                    if el['aria-expanded']:
                        print(f"    Aria-expanded: {el['aria-expanded']}")
                    if el['aria-controls']:
                        print(f"    Aria-controls: {el['aria-controls']}")
            else:
                print("\nNo new elements detected after click")

            return True

        print("Failed to click element using all strategies")
        return False

    except Exception as e:
        print(f"Error clicking element: {e}")
        return False


def clear_input_field(page):
    """Clear the current input field using Ctrl+A and Delete"""
    try:
        # On macOS, use Command instead of Control
        page.keyboard.press("Meta+a")  # Command+A on Mac
        time.sleep(0.1)
        page.keyboard.press("Backspace")
        time.sleep(0.2)  # Small delay to ensure field is cleared

        # Fallback to Control+A if Meta+A didn't work
        page.keyboard.press("Control+a")
        time.sleep(0.1)
        page.keyboard.press("Backspace")
        time.sleep(0.2)
    except Exception as e:
        print(f"Error clearing input field: {e}")


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

        # Try to get field state using multiple selectors
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
            return False
        else:
            print("Could not access field state")
            return False

    except Exception as e:
        print(f"Error in verify_field_content: {e}")
        print(f"Error type: {type(e).__name__}")
        return False


def retry_option_selection(page, new_elements, element, resume_text, excluded_options):
    """Retry option selection excluding previously tried options"""
    try:
        print(f"\nExcluding options: {excluded_options}")

        # Filter out previously tried options
        available_elements = []
        original_to_new_index = {}  # Map to track original indices
        new_index = 0

        # Create a filtered list and mapping
        for original_index, el in enumerate(new_elements):
            if original_index not in excluded_options:
                available_elements.append(el)
                original_to_new_index[new_index] = original_index
                new_index += 1

        if not available_elements:
            print("No more options to try")
            return None

        print(f"\nNumber of remaining options: {len(available_elements)}")

        # Create elements text with NEW indices (only for available elements)
        elements_text = "\n".join(
            [f"[{i}] {el.get('text', '')}" for i, el in enumerate(available_elements)])

        # Show what options we're excluding
        excluded_text = ", ".join(
            [f"'{new_elements[i]['text']}'" for i in excluded_options])

        message = f"""Given these remaining dropdown options and the candidate's resume, previous attempts failed to select the correct option.
        Find the single best remaining option that looks like a valid dropdown choice.
        Return ONLY the NUMBER of that one best option from the list below.
        If none of the remaining options appear to be valid matches, return exactly the word 'false'.
        
        Question/Field: {element['label']}
        Previously tried and excluded options: {excluded_text}
        Number of remaining options: {len(available_elements)}
        
        Available options (with new numbering):
        {elements_text}
        
        Resume:
        {resume_text}
        """

        response = client.chat.completions.create(
            model="gpt-4o",  # Use the most capable model for retries
            messages=[{"role": "user", "content": message}],
            temperature=0.1
        )

        answer = response.choices[0].message.content.strip().lower()
        print(f"\nGPT suggests new option number or false: {answer}")

        if answer == 'false':
            return None

        try:
            # Get the new index from GPT's response
            new_index = int(''.join(filter(str.isdigit, answer)))

            # Verify the new index is within bounds of available options
            if 0 <= new_index < len(available_elements):
                original_index = original_to_new_index[new_index]
                print(
                    f"Mapped new index {new_index} to original index {original_index}")
                print(
                    f"Selected text: '{available_elements[new_index].get('text', '')}'")
                return original_index
            else:
                print(
                    f"New index {new_index} out of range for available options (0-{len(available_elements)-1})")
                return None

        except ValueError:
            print("Could not extract valid number from GPT response")
            return None

    except Exception as e:
        print(f"Error in retry_option_selection: {e}")
        return None


def truncate(text, length=30):
    """Truncate text to specified length"""
    return text[:length] + "..." if len(str(text)) > length else text


def print_elements_list(elements, prefix=""):
    """Print elements list with indices"""
    print(f"\n{prefix} ({len(elements)} items):")
    for i, el in enumerate(elements):
        text = el.get('text', '')
        print(f"  [{i}] {truncate(text)}")


def reset_focus(page, element):
    """Reset focus by clicking away and then back to the target element"""
    try:
        print("\nResetting focus...")
        # Click on the body or a safe area to deselect everything
        page.evaluate('''() => {
            // Try to find a safe area to click (preferably empty space)
            const safeElements = [
                document.body,
                document.querySelector('main'),
                document.querySelector('form'),
                document.querySelector('div:empty')
            ].filter(el => el);
            
            if (safeElements.length > 0) {
                safeElements[0].click();
                return true;
            }
            return false;
        }''')
        time.sleep(0.5)  # Wait for any dropdowns to close

        # Click back on our target element
        clicked = False
        if element['attributes']['id']:
            try:
                page.click(f"#{element['attributes']['id']}")
                print("Refocused on element by ID")
                clicked = True
            except:
                pass

        if not clicked and element['xpath']:
            try:
                page.click(f"xpath={element['xpath']}")
                print("Refocused on element by XPath")
                clicked = True
            except:
                pass

        if not clicked and element['attributes']['role'] and element['label']:
            try:
                page.get_by_role(element['attributes']
                                 ['role'], name=element['label']).click()
                print("Refocused on element by role and label")
                clicked = True
            except:
                pass

        time.sleep(0.5)  # Wait for element to be ready
        return clicked

    except Exception as e:
        print(f"Error in reset_focus: {e}")
        return False


def click_and_type_dropdown(page, element):
    """Click dropdown and type the GPT-suggested search term with retries"""
    try:
        # Get elements before clicking
        before_elements = get_current_elements(page)

        # Load resume text
        with open('info.txt', 'r') as file:
            resume_text = file.read()

        # Initial click on the dropdown
        clicked = False
        if element['attributes']['id']:
            try:
                page.click(f"#{element['attributes']['id']}")
                print(f"Clicked element by ID: {element['attributes']['id']}")
                clicked = True
            except:
                pass

        if not clicked and element['xpath']:
            try:
                page.click(f"xpath={element['xpath']}")
                print(f"Clicked element by XPath")
                clicked = True
            except:
                pass

        if not clicked and element['attributes']['role'] and element['label']:
            try:
                page.get_by_role(element['attributes']
                                 ['role'], name=element['label']).click()
                print(f"Clicked element by role and label")
                clicked = True
            except:
                pass

        if clicked:
            max_attempts = 10
            attempt = 0

            while attempt < max_attempts:
                attempt += 1
                print(f"\nAttempt {attempt} of {max_attempts}")

                # Reset focus between attempts after the first one
                if attempt > 1:
                    if not reset_focus(page, element):
                        print("Failed to reset focus, continuing anyway...")
                    time.sleep(0.5)

                # Clear field
                print("Clearing input...")
                clear_input_field(page)
                time.sleep(0.5)
                before_elements = get_current_elements(page)

                # Get new search term
                search_term = get_dropdown_suggestion(
                    element, resume_text, attempt)
                if not search_term:
                    print("Failed to get search suggestion from GPT")
                    continue

                print(f"Typing search term: {search_term}")
                page.keyboard.type(search_term)
                time.sleep(0.5)  # Wait for dropdown to update

                # Get new elements after typing
                after_elements = get_current_elements(page)
                new_elements = compare_elements(
                    before_elements, after_elements)

                if new_elements:
                    print("\nNewly added elements after typing:")
                    for i, el in enumerate(new_elements):
                        print(f"\n[{i}] New Element:")
                        if el['text']:
                            print(f"    Text: {el['text']}")
                        if el['role']:
                            print(f"    Role: {el['role']}")
                        if el['type']:
                            print(f"    Type: {el['type']}")
                        if el['class']:
                            print(f"    Class: {el['class']}")
                        if el['aria-expanded']:
                            print(f"    Aria-expanded: {el['aria-expanded']}")
                        if el['aria-controls']:
                            print(f"    Aria-controls: {el['aria-controls']}")

                    # Track tried options and maintain running list of available options
                    running_elements = new_elements.copy()  # Create a copy to modify

                    while running_elements:  # Continue while we have options
                        print("\n" + "="*50)
                        print_elements_list(
                            running_elements, "Current options list")

                        if len(running_elements) == 1:
                            option_number = 0
                            print(
                                f"Only one option left, using index {option_number}")
                        else:
                            option_number = get_best_option_number(
                                running_elements, element['label'], resume_text)

                        if option_number == 'false' or option_number is None:
                            print("No valid match found in current options")
                            break

                        if not isinstance(option_number, int) or option_number < 0 or option_number >= len(running_elements):
                            print(
                                f"Invalid option number returned: {option_number}")
                            break

                        selected_element = running_elements[option_number]
                        print(
                            f"\nSelected option [{option_number}]: {truncate(selected_element.get('text', ''))}")

                        try:
                            if selected_element.get('text'):
                                page.get_by_text(
                                    selected_element['text'], exact=True).click()
                                print(
                                    f"Clicked option: {truncate(selected_element['text'])}")

                                # Verify if field has content
                                time.sleep(0.5)
                                if verify_field_content(page, element):
                                    print("Field successfully populated")
                                    return True
                                else:
                                    print("\nField still empty after selection")
                                    removed_element = running_elements.pop(
                                        option_number)
                                    print(
                                        f"Removed option [{option_number}]: {truncate(removed_element.get('text', ''))}")

                                    # Only retype search term if using GPT-4o
                                    if attempt >= len(models):  # We're using GPT-4o
                                        print(
                                            f"\nRetyping last search term: {search_term}")
                                        page.keyboard.type(search_term)
                                        # Wait for dropdown to update
                                        time.sleep(0.5)
                                        continue
                                    else:
                                        print(
                                            "Moving to next model for new search term...")
                                        break  # Break inner loop to try new search term

                        except Exception as e:
                            print(f"Error clicking option: {truncate(str(e))}")
                            removed_element = running_elements.pop(
                                option_number)
                            print(
                                f"Removed option [{option_number}]: {truncate(removed_element.get('text', ''))}")

                            # Only retype search term if using GPT-4o
                            if attempt >= len(models):  # We're using GPT-4o
                                print(
                                    f"\nRetyping last search term: {search_term}")
                                page.keyboard.type(search_term)
                                time.sleep(0.5)  # Wait for dropdown to update
                                continue
                            else:
                                print("Moving to next model for new search term...")
                                break  # Break inner loop to try new search term

                    print(
                        f"\nNo more options to try (started with {len(new_elements)}, remaining: {len(running_elements)})")
                else:
                    print(
                        "\nNo new elements detected after typing, trying another search term...")
                    continue

            print(f"\nFailed to find a match after {max_attempts} attempts")
            return False

        print("Failed to click element using all strategies")
        return False

    except Exception as e:
        print(f"Error in click_and_type_dropdown: {e}")
        return False


def main():
    try:
        # Initialize browser and get pages
        chrome_process, playwright, browser, pages = initialize_browser()

        # Analyze forms on first page
        clickable_elements = analyze_form_fields(pages[0])

        while True:
            try:
                choice = input(
                    "\nEnter element number to click (or 'q' to quit): ")
                if choice.lower() == 'q':
                    break

                element_index = int(choice)
                if 0 <= element_index < len(clickable_elements):
                    element = clickable_elements[element_index]
                    if element['type'] == 'dropdown':
                        click_and_type_dropdown(pages[0], element)
                    else:
                        click_element(pages[0], element)
                else:
                    print("Invalid element number")
            except ValueError:
                print("Please enter a valid number or 'q' to quit")

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
