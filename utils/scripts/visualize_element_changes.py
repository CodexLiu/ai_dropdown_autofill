from utils.scripts.get_detailed_element_info import get_detailed_element_info
from utils.scripts.reset_focus import reset_focus
from utils.gpt.option_selector import select_best_option
from utils.gpt.field_partial_fill import generate_search_term
from utils.gpt.field_partial_fill_with_retry import generate_retry_search_term
from utils.gpt.field_fill_no_context import generate_search_term as generate_search_term_no_context
from utils.scripts.compare_utils import compare_states, compare_styles, compare_aria
import time
from datetime import datetime


def visualize_element_changes(page, element, analyze_form_fields_func):
    """Visualize changes in the element and its surroundings"""
    while True:
        print("\n=== Element Visualization Start ===")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")

        # Get initial state
        print("\nGetting initial state...")
        initial_state = get_detailed_element_info(page, element)
        print(f"Initial state keys: {list(initial_state.keys())}")
        if 'targetElement' in initial_state:
            print(
                f"Initial targetElement keys: {list(initial_state['targetElement'].keys())}")

        # Click the element
        try:
            if element['attributes']['id']:
                # Escape periods in ID for CSS selector
                escaped_id = element['attributes']['id'].replace('.', '\\.')
                page.click(f"#{escaped_id}")
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
        print(f"Post state keys: {list(post_state.keys())}")
        if 'targetElement' in post_state:
            print(
                f"Post targetElement keys: {list(post_state['targetElement'].keys())}")

        # Compare and display changes
        print("\n=== Changes Detected ===")

        # Compare target element
        print("\nTarget Element Changes:")
        if 'targetElement' not in initial_state or 'targetElement' not in post_state:
            print("Error: Missing targetElement in one of the states")
            print(
                f"Initial state has targetElement: {'targetElement' in initial_state}")
            print(
                f"Post state has targetElement: {'targetElement' in post_state}")
        else:
            compare_states(
                initial_state['targetElement'], post_state['targetElement'])

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
            if len(formatted_elements) >= 90:
                print("\nLarge number of options detected. Generating search term...")
                # Take first 5 elements as sample
                search_term = generate_search_term(
                    formatted_elements[:5], element['label'])
                if not search_term:
                    print(
                        "Failed to generate initial search term, trying retry functionality...")
                    search_term = generate_retry_search_term(
                        formatted_elements[:5], element['label'], "", formatted_elements)

                if search_term:
                    print(f"\nTyping search term: {search_term}")
                    try:
                        # Focus and type into the original field
                        if element['attributes']['id']:
                            escaped_id = element['attributes']['id'].replace(
                                '.', '\\.')
                            page.click(f"#{escaped_id}")
                        elif element['xpath']:
                            page.click(f"xpath={element['xpath']}")

                        # Type the search term
                        page.keyboard.type(search_term)
                        # Increased delay to wait for dropdown to update and populate
                        time.sleep(1.5)

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
                                // Try multiple common dropdown patterns
                                let options = [];
                                
                                // Try React-Select pattern
                                const listboxId = `react-select-${el.id}-listbox`;
                                const reactSelectListbox = document.getElementById(listboxId);
                                if (reactSelectListbox) {
                                    options = Array.from(reactSelectListbox.querySelectorAll('[class*="select__option"]'));
                                }
                                
                                // If no React-Select options found, try other common patterns
                                if (!options.length) {
                                    // Try aria-expanded parent pattern
                                    const expandedParent = document.querySelector('[aria-expanded="true"]');
                                    if (expandedParent) {
                                        options = Array.from(expandedParent.querySelectorAll('li, [role="option"]'));
                                    }
                                }
                                
                                // Try visible dropdown items pattern
                                if (!options.length) {
                                    options = Array.from(document.querySelectorAll('.dropdown-item:not([style*="display: none"]), [class*="dropdown"]:not([style*="display: none"]) li, .select-option:not([style*="display: none"])'));
                                }
                                
                                // If still no options found, try any visible list items near the field
                                if (!options.length) {
                                    const rect = el.getBoundingClientRect();
                                    options = Array.from(document.querySelectorAll('li, [role="option"]'))
                                        .filter(opt => {
                                            const optRect = opt.getBoundingClientRect();
                                            return optRect.top > rect.bottom && // Below the field
                                                   Math.abs(optRect.left - rect.left) < 100 && // Roughly aligned
                                                   !opt.closest('[style*="display: none"]'); // Not hidden
                                        });
                                }
                                
                                if (!options.length) {
                                    return { error: 'Could not find dropdown options' };
                                }
                                
                                return {
                                    allVisibleElements: options.map(opt => ({
                                        tag: opt.tagName.toLowerCase(),
                                        id: opt.id,
                                        textContent: opt.textContent.trim(),
                                        classes: Array.from(opt.classList)
                                    }))
                                };
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

                                # Get GPT's selection
                                best_option = select_best_option(
                                    formatted_elements,
                                    element['label']
                                )

                                if best_option != 'false':
                                    selected_element = new_elements[best_option]
                                    print(
                                        f"\nGPT selected option {best_option + 1}")

                                    # Try clicking by various methods
                                    try:
                                        if selected_element['id']:
                                            escaped_id = selected_element['id'].replace(
                                                '.', '\\.')
                                            page.click(f"#{escaped_id}")
                                        elif selected_element['textContent']:
                                            page.get_by_text(
                                                selected_element['textContent'], exact=True).click()
                                        print(
                                            f"\nClicked element {best_option + 1}")

                                        # Reset focus after clicking
                                        time.sleep(0.1)
                                        reset_focus(page, element)
                                        time.sleep(0.1)  # Wait for focus reset
                                        # Return and exit after successful selection
                                        return analyze_form_fields_func(page)
                                    except Exception as e:
                                        print(f"Error clicking element: {e}")
                                        print("Clearing search term...")
                                        page.keyboard.press("Control+a")
                                        page.keyboard.press("Backspace")
                                else:
                                    # TODO: omg please fix this later i have sucha  bad headache
                                    print(
                                        "GPT couldn't determine the best option")
                                    # Try generating a new search term based on the failed results
                                    retry_search_term = generate_retry_search_term(
                                        formatted_elements[:5],
                                        element['label'],
                                        search_term,
                                        formatted_elements
                                    )

                                    if retry_search_term:
                                        print(
                                            f"\nTrying new search term: {retry_search_term}")
                                        # Clear previous search
                                        page.keyboard.press("Control+a")
                                        page.keyboard.press("Backspace")
                                        time.sleep(0.5)

                                        # Type new search term
                                        page.keyboard.type(retry_search_term)
                                        # Wait for dropdown to update
                                        time.sleep(2.5)

                                        # Continue with the same logic for handling search results...
                                        continue

                                    print("Clearing search term...")
                                    page.keyboard.press("Control+a")
                                    page.keyboard.press("Backspace")
                            else:
                                print("No matches found with search term")
                                print("Clearing search term...")
                                page.keyboard.press("Control+a")
                                page.keyboard.press("Backspace")
                        except Exception as e:
                            print(f"Error getting updated state: {str(e)}")
                            print("Clearing search term...")
                            page.keyboard.press("Control+a")
                            page.keyboard.press("Backspace")
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
                        escaped_id = selected_element['id'].replace('.', '\\.')
                        page.click(f"#{escaped_id}")
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
                                escaped_id = selected_element['id'].replace(
                                    '.', '\\.')
                                page.click(f"#{escaped_id}")
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
                            escaped_id = selected_element['id'].replace(
                                '.', '\\.')
                            page.click(f"#{escaped_id}")
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

            # First check if this is a native select with options
            native_options = page.evaluate('''(elementInfo) => {
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
                
                // Check if it's a select element and has options
                if (el.tagName.toLowerCase() === 'select') {
                    return Array.from(el.querySelectorAll('option'))
                        .filter(opt => {
                            // Skip the "Please Select" or empty options
                            const text = opt.textContent.trim().toLowerCase();
                            const value = (opt.value || '').trim();
                            return !opt.disabled && 
                                   value && 
                                   value !== 'Please Select' &&
                                   !text.includes('please select') &&
                                   !text.includes('select...') &&
                                   value !== '-1' &&
                                   value !== '';
                        })
                        .map(opt => ({
                            text: opt.textContent.trim(),
                            value: opt.value,
                            selected: opt.selected,
                            // Include any additional attributes that might be useful
                            attributes: {
                                class: opt.className,
                                id: opt.id,
                                'data-value': opt.getAttribute('data-value'),
                                'aria-label': opt.getAttribute('aria-label')
                            }
                        }));
                }
                
                return [];
            }''', {
                'id': element['attributes']['id'],
                'xpath': element['xpath']
            })

            if native_options and len(native_options) > 0:
                print(f"\nFound {len(native_options)} native select options")

                # Format options for GPT
                formatted_elements = [
                    {
                        'text': opt['text'],
                        'class': ''  # Native options don't have classes
                    }
                    for opt in native_options
                ]

                # Get GPT's selection
                best_option = select_best_option(
                    formatted_elements,
                    element['label']
                )

                if best_option != 'false':
                    selected_option = native_options[best_option]
                    print(f"\nGPT selected option: {selected_option['text']}")

                    try:
                        # Use JavaScript to set the value
                        page.evaluate('''(params) => {
                            function getFieldByMultipleMethods() {
                                let el;
                                
                                // Try by ID
                                const id = params.elementInfo.id;
                                if (id) {
                                    el = document.getElementById(id);
                                    if (el) return { method: 'id', element: el };
                                }
                                
                                // Try by XPath
                                const xpath = params.elementInfo.xpath;
                                if (xpath) {
                                    el = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                                    if (el) return { method: 'xpath', element: el };
                                }
                                
                                return null;
                            }

                            const result = getFieldByMultipleMethods();
                            if (!result) return false;
                            
                            const el = result.element;
                            el.value = params.value;
                            
                            // Trigger change event
                            const event = new Event('change', { bubbles: true });
                            el.dispatchEvent(event);
                            
                            return true;
                        }''', {
                            'elementInfo': {
                                'id': element['attributes']['id'],
                                'xpath': element['xpath']
                            },
                            'value': selected_option['value']
                        })

                        print("Successfully set select value")
                        time.sleep(0.1)
                        break
                    except Exception as e:
                        print(f"Error setting select value: {e}")
                else:
                    print(
                        "GPT couldn't determine the best option from native select options")

            # If no native options or selection failed, try search term approach
            print("Attempting to type a search term...")
            search_term = generate_search_term_no_context(element['label'])

            if search_term:
                print(f"\nTyping search term: {search_term}")
                try:
                    # Focus and type into the original field
                    if element['attributes']['id']:
                        escaped_id = element['attributes']['id'].replace(
                            '.', '\\.')
                        page.click(f"#{escaped_id}")
                    elif element['xpath']:
                        page.click(f"xpath={element['xpath']}")

                    # Type the search term
                    page.keyboard.type(search_term)
                    # Increased delay to wait for dropdown to update and populate
                    time.sleep(2.5)

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
                            // Try multiple common dropdown patterns
                            let options = [];
                            
                            // Try React-Select pattern
                            const listboxId = `react-select-${el.id}-listbox`;
                            const reactSelectListbox = document.getElementById(listboxId);
                            if (reactSelectListbox) {
                                options = Array.from(reactSelectListbox.querySelectorAll('[class*="select__option"]'));
                            }
                            
                            // If no React-Select options found, try other common patterns
                            if (!options.length) {
                                // Try aria-expanded parent pattern
                                const expandedParent = document.querySelector('[aria-expanded="true"]');
                                if (expandedParent) {
                                    options = Array.from(expandedParent.querySelectorAll('li, [role="option"]'));
                                }
                            }
                            
                            // Try visible dropdown items pattern
                            if (!options.length) {
                                options = Array.from(document.querySelectorAll('.dropdown-item:not([style*="display: none"]), [class*="dropdown"]:not([style*="display: none"]) li, .select-option:not([style*="display: none"])'));
                            }
                            
                            // If still no options found, try any visible list items near the field
                            if (!options.length) {
                                const rect = el.getBoundingClientRect();
                                options = Array.from(document.querySelectorAll('li, [role="option"]'))
                                    .filter(opt => {
                                        const optRect = opt.getBoundingClientRect();
                                        return optRect.top > rect.bottom && // Below the field
                                               Math.abs(optRect.left - rect.left) < 100 && // Roughly aligned
                                               !opt.closest('[style*="display: none"]'); // Not hidden
                                    });
                            }
                            
                            if (!options.length) {
                                return { error: 'Could not find dropdown options' };
                            }
                            
                            return {
                                allVisibleElements: options.map(opt => ({
                                    tag: opt.tagName.toLowerCase(),
                                    id: opt.id,
                                    textContent: opt.textContent.trim(),
                                    classes: Array.from(opt.classList)
                                }))
                            };
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

                            # Get GPT's selection
                            best_option = select_best_option(
                                formatted_elements,
                                element['label']
                            )

                            if best_option != 'false':
                                selected_element = new_elements[best_option]
                                print(
                                    f"\nGPT selected option {best_option + 1}")

                                # Try clicking by various methods
                                try:
                                    if selected_element['id']:
                                        escaped_id = selected_element['id'].replace(
                                            '.', '\\.')
                                        page.click(f"#{escaped_id}")
                                    elif selected_element['textContent']:
                                        page.get_by_text(
                                            selected_element['textContent'], exact=True).click()
                                    print(
                                        f"\nClicked element {best_option + 1}")

                                    # Reset focus after clicking
                                    time.sleep(0.1)
                                    reset_focus(page, element)
                                    time.sleep(0.1)  # Wait for focus reset
                                    # Return and exit after successful selection
                                    return analyze_form_fields_func(page)
                                except Exception as e:
                                    print(f"Error clicking element: {e}")
                                    print("Clearing search term...")
                                    page.keyboard.press("Control+a")
                                    page.keyboard.press("Backspace")
                            else:
                                print("GPT couldn't determine the best option")
                                # Try generating a new search term based on the failed results
                                retry_search_term = generate_retry_search_term(
                                    formatted_elements[:5],
                                    element['label'],
                                    search_term,
                                    formatted_elements
                                )

                                if retry_search_term:
                                    print(
                                        f"\nTrying new search term: {retry_search_term}")
                                    # Clear previous search
                                    page.keyboard.press("Control+a")
                                    page.keyboard.press("Backspace")
                                    time.sleep(0.5)

                                    # Type new search term
                                    page.keyboard.type(retry_search_term)
                                    # Wait for dropdown to update
                                    time.sleep(2.5)

                                    # Continue with the same logic for handling search results...
                                    continue

                                print("Clearing search term...")
                                page.keyboard.press("Control+a")
                                page.keyboard.press("Backspace")
                        else:
                            print("No matches found with search term")
                            print("Clearing search term...")
                            page.keyboard.press("Control+a")
                            page.keyboard.press("Backspace")
                    except Exception as e:
                        print(f"Error getting updated state: {str(e)}")
                        print("Clearing search term...")
                        page.keyboard.press("Control+a")
                        page.keyboard.press("Backspace")
                except Exception as e:
                    print(f"Error using search functionality: {e}")
                    # Clear any partial input
                    try:
                        page.keyboard.press("Control+a")
                        page.keyboard.press("Backspace")
                    except:
                        pass
            else:
                print("Could not generate search term")
            break

        print("\n=== Element Visualization End ===")
        break

    # Reset focus one final time before re-analyzing
    reset_focus(page, element)
    time.sleep(0.1)

    # Re-analyze all form fields
    print("\nRe-analyzing all form fields...")
    return analyze_form_fields_func(page)
