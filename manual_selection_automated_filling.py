from playwright.sync_api import sync_playwright
from test_case import initialize_browser
from utils.gpt.option_selector import select_best_option
from utils.gpt.field_partial_fill import generate_search_term
import time
from datetime import datetime


def verify_field_content(page, element):
    """Check if a field has actual selected content (not placeholder text)"""
    try:
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
            # Check for actual selected value
            value_fields = ['selectedText',
                            'selectedAriaText', 'value', 'ariaValue']
            for field in value_fields:
                value = field_state.get(field, '').strip()
                if value:
                    # Check if it's not a placeholder
                    if not any(text in value.lower() for text in [
                        "select...", "all selected options have been cleared",
                        "choose an option", "no selection", "select an option"
                    ]):
                        return True
            return False
        else:
            return False

    except Exception as e:
        print(f"Error in verify_field_content: {e}")
        return False


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

            return {
                type: el.tagName.toLowerCase(),
                label: getLabel(el),
                value: el.value || '',
                isEmpty: !el.value,
                isRequired: el.required || el.getAttribute('aria-required') === 'true',
                isVisible: el.offsetParent !== null,
                isEnabled: !el.disabled,
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

        function getXPath(el) {
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
        }

        // Get all elements
        function getElementBounds(el) {
            const rect = el.getBoundingClientRect();
            return {
                top: rect.top,
                right: rect.right,
                bottom: rect.bottom,
                left: rect.left,
                width: rect.width,
                height: rect.height
            };
        }

        function findCommonAncestor(el1, el2) {
            const path1 = [];
            let parent = el1;
            while (parent) {
                path1.push(parent);
                parent = parent.parentElement;
            }
            
            parent = el2;
            while (parent) {
                if (path1.includes(parent)) {
                    return parent;
                }
                parent = parent.parentElement;
            }
            return null;
        }

        function elementsOverlap(el1, el2) {
            const rect1 = getElementBounds(el1);
            const rect2 = getElementBounds(el2);
            
            // Check if elements are close to each other (within 50px)
            const closeHorizontally = Math.abs(rect1.left - rect2.left) < 50 || 
                                    Math.abs(rect1.right - rect2.right) < 50;
            const closeVertically = Math.abs(rect1.top - rect2.top) < 50 || 
                                  Math.abs(rect1.bottom - rect2.bottom) < 50;
            
            // Check if elements share common ancestor within 3 levels
            const commonAncestor = findCommonAncestor(el1, el2);
            const closeAncestor = commonAncestor && 
                                Array.from(commonAncestor.querySelectorAll('*')).length < 20;
            
            return (closeHorizontally && closeVertically) || closeAncestor;
        }

        // First get all potential form elements
        const elements = Array.from(document.querySelectorAll('*'))
            .filter(el => {
                const style = window.getComputedStyle(el);
                const tag = el.tagName.toLowerCase();
                
                // Only keep form-related elements
                const allowedTags = ['input', 'button', 'textarea', 'fieldset', 'select'];
                const isFormElement = allowedTags.includes(tag);
                
                // Also keep elements with form-related roles
                const formRoles = ['button', 'checkbox', 'combobox', 'listbox', 'menuitem', 
                                 'menuitemcheckbox', 'menuitemradio', 'option', 'radio', 
                                 'searchbox', 'switch', 'tab', 'textbox'];
                const hasFormRole = formRoles.includes(el.getAttribute('role'));
                
                return (isFormElement || hasFormRole) && 
                       style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0' &&
                       el.offsetParent !== null;
            });

        // Group related elements
        const groups = [];
        const usedElements = new Set();

        elements.forEach(el => {
            if (usedElements.has(el)) return;
            
            const group = [el];
            usedElements.add(el);
            
            // Find related elements
            elements.forEach(otherEl => {
                if (el === otherEl || usedElements.has(otherEl)) return;
                
                if (elementsOverlap(el, otherEl)) {
                    group.push(otherEl);
                    usedElements.add(otherEl);
                }
            });
            
            groups.push(group);
        });

        // Map groups to field details
        return groups.map(group => {
            // Find the main input element in the group
            const mainElement = group.find(el => 
                el.tagName.toLowerCase() === 'input' || 
                el.getAttribute('role') === 'combobox' ||
                el.getAttribute('role') === 'textbox'
            ) || group[0];  // Fallback to first element if no input found
            
            const details = getFieldDetails(mainElement);
            
            // Add related elements information
            details.relatedElements = group
                .filter(el => el !== mainElement)
                .map(el => ({
                    type: el.tagName.toLowerCase(),
                    role: el.getAttribute('role'),
                    class: el.className,
                    id: el.id,
                    label: el.getAttribute('aria-label') || ''
                }));
            
            return details;
        });
    }''')

    # Store all fields with their indices
    clickable_elements = []
    current_index = 0

    # Group fields by type
    print("\n=== Element Analysis ===")
    for field in form_fields:
        # Skip if the main element is a button or contains 'attach' in label
        if (field['type'] == 'button' or
            field['attributes']['role'] == 'button' or
            'btn' in (field['attributes']['class'] or '').lower() or
            'button' in (field['attributes']['class'] or '').lower() or
                'attach' in (field['label'] or '').lower()):
            continue

        # Check if the field has any related button elements
        has_button = False
        if field.get('relatedElements'):
            for rel in field['relatedElements']:
                if (rel['type'] == 'button' or
                    rel['role'] == 'button' or
                    'btn' in (rel['class'] or '').lower() or
                        'button' in (rel['class'] or '').lower()):
                    has_button = True
                    break

        # Only display and store elements that have related buttons
        if has_button:
            print(f"\n[{current_index}] Main Element:")
            print(f"    Type: {field['type']}")
            print(f"    Label: {field['label']}")
            print(f"    Role: {field['attributes']['role']}")
            print(f"    Class: {field['attributes']['class']}")
            print(f"    ID: {field['attributes']['id']}")

            # Check if field is empty
            is_empty = verify_field_content(page, field)
            print(
                f"    Content Status: {'Empty' if not is_empty else 'Has Content'}")

            if field.get('relatedElements'):
                print("    Related Elements:")
                for rel in field['relatedElements']:
                    print(
                        f"      - {rel['type']} ({rel['role'] or 'no role'}) {rel['label']}")
                    if rel['id']:
                        print(f"        ID: {rel['id']}")
                    if rel['class']:
                        print(f"        Class: {rel['class']}")

            clickable_elements.append(field)
            current_index += 1

    return clickable_elements


def get_detailed_element_info(page, element):
    """Get detailed information about an element and its surroundings"""
    return page.evaluate('''(xpath) => {
        function getElementByXPath(xpath) {
            return document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        }

        const el = getElementByXPath(xpath);
        if (!el) return { error: 'Element not found' };

        function getComputedStyleProperties(element) {
            const style = window.getComputedStyle(element);
            return {
                position: style.position,
                display: style.display,
                visibility: style.visibility,
                opacity: style.opacity,
                zIndex: style.zIndex,
                backgroundColor: style.backgroundColor,
                color: style.color,
                width: style.width,
                height: style.height,
                padding: style.padding,
                margin: style.margin,
                border: style.border,
                boxShadow: style.boxShadow,
                transform: style.transform
            };
        }

        function getElementDetails(element) {
            // Get any associated label
            let labelText = '';
            if (element.id) {
                const label = document.querySelector(`label[for="${element.id}"]`);
                if (label) labelText = label.textContent.trim();
            }
            
            // Check if element is truly hidden
            const style = window.getComputedStyle(element);
            const isHiddenByStyle = style.display === 'none' || 
                                  style.visibility === 'hidden' || 
                                  style.opacity === '0';
            const isHiddenByDimensions = element.offsetWidth === 0 && 
                                       element.offsetHeight === 0;
            const isHiddenByOverflow = element.offsetParent === null && 
                                     style.position !== 'fixed' && 
                                     style.position !== 'absolute';
            
            // Special handling for inputs and selects
            const isFormField = element.tagName.toLowerCase() === 'input' || 
                              element.tagName.toLowerCase() === 'select' ||
                              element.getAttribute('role') === 'combobox' ||
                              element.getAttribute('role') === 'listbox';
            
            // Check if element has any interaction handlers
            const hasHandlers = element.onclick || 
                              element.onmousedown || 
                              element.onmouseup || 
                              element.onmouseover ||
                              element.onkeydown || 
                              element.onkeyup || 
                              element.onkeypress ||
                              element.getAttribute('onclick');

            return {
                tag: element.tagName.toLowerCase(),
                id: element.id,
                classes: Array.from(element.classList),
                attributes: Array.from(element.attributes).map(attr => ({
                    name: attr.name,
                    value: attr.value
                })),
                textContent: element.textContent.trim(),
                value: element.value || '',
                dimensions: element.getBoundingClientRect(),
                computedStyle: getComputedStyleProperties(element),
                isVisible: !isHiddenByStyle && !isHiddenByDimensions && !isHiddenByOverflow,
                isFormField: isFormField,
                hasMouseListeners: hasHandlers,
                hasKeyboardListeners: !!element.onkeydown || 
                                    !!element.onkeyup || 
                                    !!element.onkeypress,
                ariaAttributes: {
                    role: element.getAttribute('role'),
                    label: element.getAttribute('aria-label') || labelText,
                    description: element.getAttribute('aria-description'),
                    expanded: element.getAttribute('aria-expanded'),
                    controls: element.getAttribute('aria-controls'),
                    selected: element.getAttribute('aria-selected'),
                    hidden: element.getAttribute('aria-hidden'),
                    value: element.getAttribute('aria-value'),
                    checked: element.getAttribute('aria-checked')
                }
            };
        }

        // Get ALL visible elements in the document, including form fields regardless of visibility
        function getAllVisibleElements() {
            return Array.from(document.querySelectorAll('*'))
                .filter(el => {
                    const style = window.getComputedStyle(el);
                    const isFormField = el.tagName.toLowerCase() === 'input' || 
                                      el.tagName.toLowerCase() === 'select' ||
                                      el.getAttribute('role') === 'combobox' ||
                                      el.getAttribute('role') === 'listbox';
                    
                    // Always include form fields, even if they appear hidden
                    if (isFormField) return true;
                    
                    // For other elements, check visibility
                    return style.display !== 'none' && 
                           style.visibility !== 'hidden' && 
                           style.opacity !== '0' &&
                           el.offsetParent !== null;
                })
                .map(getElementDetails);
        }

        // Get parent chain (up to 3 levels)
        let parentChain = [];
        let parent = el.parentElement;
        let level = 0;
        while (parent && level < 3) {
            parentChain.push(getElementDetails(parent));
            parent = parent.parentElement;
            level++;
        }

        // Get siblings
        const siblings = Array.from(el.parentElement?.children || [])
            .filter(child => child !== el)
            .map(getElementDetails);

        // Get ALL children recursively
        function getAllChildren(element) {
            const children = [];
            function traverse(el) {
                Array.from(el.children).forEach(child => {
                    children.push(getElementDetails(child));
                    traverse(child);
                });
            }
            traverse(element);
            return children;
        }

        return {
            timestamp: new Date().toISOString(),
            targetElement: getElementDetails(el),
            parentChain,
            siblings,
            children: getAllChildren(el),
            allVisibleElements: getAllVisibleElements(),
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight,
                scrollX: window.scrollX,
                scrollY: window.scrollY
            }
        };
    }''', element['xpath'])


def reset_focus(page, element):
    """Reset focus using the blur() function"""
    try:
        print("\nResetting focus...")

        # Use JavaScript's blur() to unfocus the active element
        page.evaluate('''() => {
            if (document.activeElement) {
                document.activeElement.blur();
            }
        }''')
        time.sleep(0.1)

        return True

    except Exception as e:
        print(f"Error in reset_focus: {e}")
        return False


def visualize_element_changes(page, element):
    """Visualize changes in the element and its surroundings"""
    while True:
        print("\n=== Element Visualization Start ===")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")

        # Get initial state
        print("\nGetting initial state...")
        initial_state = get_detailed_element_info(page, element)

        # Click the element
        try:
            if element['attributes']['id']:
                page.click(f"#{element['attributes']['id']}")
            elif element['xpath']:
                page.click(f"xpath={element['xpath']}")
            print("\nElement clicked successfully")
        except Exception as e:
            print(f"\nFailed to click element: {e}")
            return

        # Wait a moment for changes
        time.sleep(0.1)

        # Get state after click
        print("\nGetting post-click state...")
        post_state = get_detailed_element_info(page, element)

        # Compare and display changes
        print("\n=== Changes Detected ===")

        # Compare target element
        print("\nTarget Element Changes:")
        compare_states(initial_state['targetElement'],
                       post_state['targetElement'])

        # Find new elements by comparing all visible elements
        initial_elements = {f"{el['tag']}_{el['id']}_{el['textContent']}"
                            for el in initial_state['allVisibleElements']}

        # Filter for only clickable new elements, excluding 'attach' fields
        new_elements = [el for el in post_state['allVisibleElements']
                        if f"{el['tag']}_{el['id']}_{el['textContent']}" not in initial_elements
                        and (el['hasMouseListeners'] or  # Has click handlers
                             el['ariaAttributes']['role'] in ['option', 'menuitem', 'button', 'link'] or
                             el['tag'] in ['button', 'a', 'input', 'select', 'option'] or
                             any(cls for cls in el['classes'] if 'clickable' in cls.lower(
                             ) or 'selectable' in cls.lower())
                             )
                        and not ('attach' in (el['textContent'] or '').lower() or
                                 'attach' in (el['ariaAttributes'].get('label') or '').lower())]

        if new_elements:
            print("\nNew Clickable Elements Detected:")
            for i, el in enumerate(new_elements, 1):
                print(f"\n  {i}. {el['tag'].upper()}")
                if el['textContent']:
                    print(f"     Text: {el['textContent'][:100]}")
                if el['classes']:
                    print(f"     Classes: {', '.join(el['classes'])}")
                if el['ariaAttributes']['role']:
                    print(f"     Role: {el['ariaAttributes']['role']}")
                if el['ariaAttributes']['selected']:
                    print(f"     Selected: {el['ariaAttributes']['selected']}")
                if el['ariaAttributes']['value']:
                    print(f"     Value: {el['ariaAttributes']['value']}")
                print(
                    f"     Position: (top: {el['dimensions']['top']:.0f}, left: {el['dimensions']['left']:.0f})")

            # Format elements for GPT
            formatted_elements = [
                {
                    'text': el['textContent'],
                    'class': ' '.join(el['classes'])
                }
                for el in new_elements
            ]

            # If there are 15 or more options, try to narrow down first
            if len(formatted_elements) >= 15:
                print("\nLarge number of options detected. Generating search term...")
                # Take first 5 elements as sample
                search_term = generate_search_term(
                    formatted_elements[:5], element['label'])

                if search_term:
                    print(f"\nTyping search term: {search_term}")
                    try:
                        # Focus and type into the original field
                        if element['attributes']['id']:
                            page.click(f"#{element['attributes']['id']}")
                        elif element['xpath']:
                            page.click(f"xpath={element['xpath']}")

                        # Type the search term
                        page.keyboard.type(search_term)
                        time.sleep(0.5)  # Wait for dropdown to update

                        # Get updated state after search using the same method as analyze_form_fields
                        print("\nGetting updated state after search...")
                        try:
                            post_search_state = page.evaluate('''(elementInfo) => {
                                function getFieldByMultipleMethods() {
                                    let el;
                                    
                                    // Try by ID
                                    const id = elementInfo.id;
                                    if (id) {
                                        el = document.getElementById(id);
                                        if (el) return { method: 'id', element: el };
                                    }
                                    
                                    // Try by XPath
                                    const xpath = elementInfo.xpath;
                                    if (xpath) {
                                        el = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                        if (el) return { method: 'xpath', element: el };
                                    }
                                    
                                    return null;
                                }

                                const result = getFieldByMultipleMethods();
                                if (!result) return { error: 'Could not find field' };
                                
                                const el = result.element;
                                
                                // Get all related elements (dropdown options)
                                const listboxId = `react-select-${el.id}-listbox`;
                                const listbox = document.getElementById(listboxId);
                                
                                if (!listbox) return { error: 'Could not find listbox' };
                                
                                // Get all option elements within the listbox
                                const options = Array.from(listbox.querySelectorAll('[class*="select__option"]'))
                                    .map(opt => ({
                                        tag: opt.tagName.toLowerCase(),
                                        id: opt.id,
                                        textContent: opt.textContent.trim(),
                                        classes: Array.from(opt.classList)
                                    }));
                                    
                                return { allVisibleElements: options };
                            }''', {
                                'id': element['attributes']['id'],
                                'xpath': element['xpath']
                            })

                            if not post_search_state or 'error' in post_search_state:
                                raise Exception(
                                    f"Error finding options: {post_search_state.get('error', 'Unknown error')}")

                            # These are all new elements since they're from the dropdown
                            filtered_elements = post_search_state['allVisibleElements']
                            print(
                                f"Found {len(filtered_elements)} dropdown options")

                            # Format filtered elements for GPT
                            formatted_elements = [
                                {
                                    'text': el['textContent'],
                                    'class': ' '.join(el['classes'])
                                }
                                for el in filtered_elements
                                if not ('attach' in (el['textContent'] or '').lower())
                            ]

                            if filtered_elements:
                                new_elements = filtered_elements
                                print(
                                    f"Filtered down to {len(formatted_elements)} options")
                            else:
                                print(
                                    "No matches found with search term, using original list")
                                # Clear the search term
                                page.keyboard.press("Control+a")
                                page.keyboard.press("Backspace")
                                time.sleep(0.1)
                        except Exception as e:
                            print(f"Error getting updated state: {str(e)}")
                            print("Falling back to original list...")
                            # Clear the search term
                            page.keyboard.press("Control+a")
                            page.keyboard.press("Backspace")
                            time.sleep(0.1)
                    except Exception as e:
                        print(f"Error using search functionality: {e}")
                        # Clear any partial input
                        try:
                            page.keyboard.press("Control+a")
                            page.keyboard.press("Backspace")
                        except:
                            pass
                        print("Continuing with original list...")

            # Get GPT's selection
            best_option = select_best_option(
                formatted_elements,
                element['label']
            )

            if best_option != 'false':
                selected_element = new_elements[best_option]
                print(f"\nGPT selected option {best_option + 1}")

                # Try clicking by various methods
                try:
                    if selected_element['id']:
                        page.click(f"#{selected_element['id']}")
                    elif selected_element['textContent']:
                        page.get_by_text(
                            selected_element['textContent'], exact=True).click()
                    print(f"\nClicked element {best_option + 1}")

                    # Reset focus after clicking
                    time.sleep(0.1)  # Wait for click to register
                    reset_focus(page, element)
                    time.sleep(0.1)  # Wait for focus reset

                    break  # Exit after successful click
                except Exception as e:
                    print(f"Error clicking element: {e}")
                    print("Falling back to manual selection...")
                    # Fall back to manual selection if GPT's choice fails
                    try:
                        choice = input(
                            "\nEnter number to click an element or 'q' to quit: ")
                        if choice.lower() == 'q':
                            break

                        element_index = int(choice) - 1
                        if 0 <= element_index < len(new_elements):
                            selected_element = new_elements[element_index]
                            if selected_element['id']:
                                page.click(f"#{selected_element['id']}")
                            elif selected_element['textContent']:
                                page.get_by_text(
                                    selected_element['textContent'], exact=True).click()
                            print(f"\nClicked element {choice}")

                            time.sleep(0.1)
                            reset_focus(page, element)
                            time.sleep(0.1)
                            break
                    except ValueError:
                        print("Please enter a valid number or 'q'")
            else:
                print(
                    "\nGPT couldn't determine the best option. Please select manually.")
                try:
                    choice = input(
                        "\nEnter number to click an element or 'q' to quit: ")
                    if choice.lower() == 'q':
                        break

                    element_index = int(choice) - 1
                    if 0 <= element_index < len(new_elements):
                        selected_element = new_elements[element_index]
                        if selected_element['id']:
                            page.click(f"#{selected_element['id']}")
                        elif selected_element['textContent']:
                            page.get_by_text(
                                selected_element['textContent'], exact=True).click()
                        print(f"\nClicked element {choice}")

                        time.sleep(0.1)
                        reset_focus(page, element)
                        time.sleep(0.1)
                        break
                except ValueError:
                    print("Please enter a valid number or 'q'")
        else:
            print("\nNo new clickable elements detected")
            break

        print("\n=== Element Visualization End ===")
        break

    # Reset focus one final time before re-analyzing
    reset_focus(page, element)
    time.sleep(0.1)

    # Re-analyze all form fields
    print("\nRe-analyzing all form fields...")
    return analyze_form_fields(page)


def compare_states(before, after):
    """Compare and print differences between two element states"""
    changes = []
    for key in before:
        if key in ['computedStyle', 'ariaAttributes', 'dimensions']:
            continue  # These are handled separately
        if before[key] != after[key]:
            changes.append(f"  {key}: {before[key]} -> {after[key]}")

    if changes:
        print("\nGeneral Changes:")
        for change in changes:
            print(change)


def compare_styles(before, after):
    """Compare and print style changes"""
    changes = []
    for key in before:
        if before[key] != after[key]:
            changes.append(f"  {key}: {before[key]} -> {after[key]}")

    if changes:
        for change in changes:
            print(change)


def compare_aria(before, after):
    """Compare and print ARIA attribute changes"""
    changes = []
    for key in before:
        if before[key] != after[key]:
            changes.append(f"  {key}: {before[key]} -> {after[key]}")

    if changes:
        for change in changes:
            print(change)


def main():
    try:
        # Initialize browser and get pages
        chrome_process, playwright, browser, pages = initialize_browser()
        time.sleep(3)  # Wait for pages to load

        # Analyze forms on first page
        clickable_elements = analyze_form_fields(pages[0])

        while True:
            try:
                choice = input(
                    "\nEnter element number to visualize, 'r' to refresh list, or 'q' to quit: ")

                if choice.lower() == 'q':
                    break
                elif choice.lower() == 'r':
                    print("\nRefreshing list of elements...")
                    clickable_elements = analyze_form_fields(pages[0])
                    continue

                element_index = int(choice)
                if 0 <= element_index < len(clickable_elements):
                    element = clickable_elements[element_index]
                    # Update clickable_elements with new analysis after visualization
                    new_elements = visualize_element_changes(pages[0], element)
                    if new_elements:
                        clickable_elements = new_elements
                else:
                    print("Invalid element number")
            except ValueError:
                if choice.lower() not in ['q', 'r']:
                    print("Please enter a valid number, 'r' to refresh, or 'q' to quit")

        input("\nPress Enter to exit...")
    except Exception as e:
        print(f"Error in main: {str(e)}")
    finally:
        # Clean up
        browser.close()
        playwright.stop()
        chrome_process.terminate()


if __name__ == "__main__":
    main()
