def verify_field_content(page, element):
    """Check if a field has actual selected content (not placeholder text)"""
    try:
        print("\n=== Field Content Verification ===")
        print(f"Checking field: {element.get('label', 'Unknown Label')}")
        print(f"Field type: {element.get('type', 'Unknown Type')}")
        print(f"Field ID: {element['attributes'].get('id', 'No ID')}")

        # Create a params object to safely pass to JavaScript
        params = {
            'id': element['attributes']['id'],
            'xpath': element['xpath'],
            'label': element['label']
        }

        field_state = page.evaluate('''(params) => {
            function getFieldByMultipleMethods() {
                let el;
                
                // Try by ID
                const id = params.id;
                if (id) {
                    el = document.getElementById(id);
                    if (el) return { method: 'id', element: el };
                }
                
                // Try by XPath
                const xpath = params.xpath;
                if (xpath) {
                    el = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                    if (el) return { method: 'xpath', element: el };
                }
                
                // Try by role and label
                const label = params.label;
                if (label) {
                    el = Array.from(document.querySelectorAll('[role="combobox"], [role="listbox"], select, input'))
                        .find(e => e.getAttribute('aria-label') === label || 
                                 document.querySelector(`label[for="${e.id}"]`)?.textContent.includes(label));
                    if (el) return { method: 'role_label', element: el };
                }
                
                return null;
            }

            const result = getFieldByMultipleMethods();
            if (!result) return { error: 'Could not find field' };
            
            const el = result.element;
            const style = window.getComputedStyle(el);
            
            // Get parent element info
            const parent = el.parentElement;
            const parentInfo = parent ? {
                tag: parent.tagName,
                class: parent.className,
                role: parent.getAttribute('role'),
                id: parent.id
            } : null;
            
            // Get all possible selected values
            const selectedValue = el.querySelector('.select__single-value, .selected-value, [class*="selected"], [class*="value"]');
            const selectedOption = el.querySelector('[aria-selected="true"]');
            const selectedText = selectedValue ? selectedValue.textContent : null;
            
            return {
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
                childElements: Array.from(el.children).map(child => ({
                    tag: child.tagName,
                    text: child.textContent,
                    class: child.className,
                    role: child.getAttribute('role'),
                    ariaSelected: child.getAttribute('aria-selected')
                }))
            };
        }''', params)

        if field_state:
            print("\nField State:")
            print(
                f"  Found by: {field_state.get('foundBy', 'Unknown method')}")
            print(f"  Tag: {field_state.get('tagName', 'Unknown')}")
            print(f"  Classes: {field_state.get('classList', 'None')}")
            print(f"  Disabled: {field_state.get('isDisabled', False)}")
            print(f"  ReadOnly: {field_state.get('isReadOnly', False)}")
            print(f"  Visibility: {field_state.get('visibility', 'Unknown')}")
            print(f"  Display: {field_state.get('display', 'Unknown')}")

            print("\nContent Values Found:")
            # Check for actual selected value
            value_fields = ['selectedText',
                            'selectedAriaText', 'value', 'ariaValue']
            for field in value_fields:
                value = field_state.get(field, '').strip()
                print(f"  {field}: '{value}'")
                if value:
                    # Check if it's not a placeholder
                    placeholder_texts = [
                        "select...", "all selected options have been cleared",
                        "choose an option", "no selection", "select an option"
                    ]
                    is_placeholder = any(text in value.lower()
                                         for text in placeholder_texts)
                    if not is_placeholder:
                        print(f"\nDecision: Has Content (Found in {field})")
                        print(f"  - Value: '{value}'")
                        print("  - Not a placeholder text")
                        return True
                    else:
                        print(f"  - '{value}' appears to be a placeholder")

            print("\nDecision: Empty")
            print("  - No valid content found in any field")
            return False
        else:
            print("\nDecision: Empty")
            print("  - Could not get field state")
            return False

    except Exception as e:
        print("\nDecision: Empty (Error)")
        print(f"  - Error in verify_field_content: {e}")
        return False
