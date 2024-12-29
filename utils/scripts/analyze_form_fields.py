from utils.scripts.verify_field_content import verify_field_content


def analyze_form_fields(page):
    """Analyze form fields and store clickable elements"""
    print(f"\n{'='*50}")
    print(f"Analyzing page: {page.url}")
    print(f"{'='*50}")

    # Get all form fields with detailed information
    form_fields = page.evaluate('''() => {
        function getFieldDetails(el) {
            // Find label text from related elements first
            const getLabelFromRelated = (el) => {
                // Find all related label elements
                const labels = el.querySelectorAll('label');
                if (labels.length > 0) {
                    // Return the text content of the first label found
                    return labels[0].textContent.trim();
                }
                return null;
            };

            // Get label through multiple methods
            const getLabel = (el) => {
                // Check explicit label with proper CSS escaping
                if (el.id) {
                    try {
                        // CSS.escape is the proper way to escape IDs for CSS selectors
                        const escapedId = CSS.escape(el.id);
                        const explicitLabel = document.querySelector(`label[for="${escapedId}"]`);
                        if (explicitLabel) return explicitLabel.textContent.trim();
                    } catch (e) {
                        // If selector fails, try alternative methods
                        console.log("Error finding label by ID, trying alternatives");
                    }
                }
                
                // Rest of the existing label finding logic
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

            // Wrap the entire function in try-catch to ensure it never fails completely
            try {
                const relatedLabel = getLabelFromRelated(el);
                return {
                    type: el.tagName.toLowerCase(),
                    label: relatedLabel || getLabel(el),
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
            } catch (e) {
                // If anything fails, return a minimal valid object
                console.log("Error in getFieldDetails, returning minimal info");
                return {
                    type: el.tagName ? el.tagName.toLowerCase() : 'unknown',
                    label: '',
                    value: '',
                    isEmpty: true,
                    isRequired: false,
                    isVisible: true,
                    isEnabled: true,
                    xpath: '',
                    attributes: {
                        id: '',
                        name: '',
                        class: '',
                        role: '',
                        'aria-label': '',
                        'aria-controls': '',
                        placeholder: ''
                    }
                };
            }
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

        // First find all select fields (both native and custom)
        const selectElements = Array.from(document.querySelectorAll('select, [role="listbox"], [role="combobox"], [class*="select"], [class*="dropdown"]'))
            .filter(el => {
                const style = window.getComputedStyle(el);
                // Be more lenient with visibility checks for select elements
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' &&
                       (el.tagName.toLowerCase() === 'select' || // Always include native select
                        (style.opacity !== '0' && el.offsetParent !== null)); // Check others
            });

        // Then get all other form elements
        const otherElements = Array.from(document.querySelectorAll('*'))
            .filter(el => {
                const style = window.getComputedStyle(el);
                const tag = el.tagName.toLowerCase();
                
                // Skip if it's already in selectElements
                if (selectElements.includes(el)) return false;
                
                // Only keep form-related elements
                const allowedTags = ['input', 'button', 'textarea', 'fieldset'];
                const isFormElement = allowedTags.includes(tag);
                
                // Also keep elements with form-related roles
                const formRoles = ['button', 'checkbox', 'menuitem', 
                                 'menuitemcheckbox', 'menuitemradio', 'option', 'radio', 
                                 'searchbox', 'switch', 'tab', 'textbox'];
                const hasFormRole = formRoles.includes(el.getAttribute('role'));
                
                return (isFormElement || hasFormRole) && 
                       style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0' &&
                       el.offsetParent !== null;
            });

        // Combine both sets of elements
        const elements = [...selectElements, ...otherElements];

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
            // For select groups, prioritize the select element as main
            const mainElement = group.find(el => 
                el.tagName.toLowerCase() === 'select' ||
                el.getAttribute('role') === 'listbox' ||
                el.getAttribute('role') === 'combobox' ||
                (el.className && (el.className.includes('select') || el.className.includes('dropdown')))
            ) || group.find(el => 
                el.tagName.toLowerCase() === 'input' || 
                el.getAttribute('role') === 'textbox'
            ) || group[0];
            
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

        # Always include select fields and elements with listbox/combobox roles
        is_select = (field['type'] == 'select' or
                     field['attributes']['role'] in ['listbox', 'combobox'])

        # For non-select fields, check if they have related button elements
        has_button = False
        if not is_select and field.get('relatedElements'):
            for rel in field['relatedElements']:
                if (rel['type'] == 'button' or
                    rel['role'] == 'button' or
                    'btn' in (rel['class'] or '').lower() or
                        'button' in (rel['class'] or '').lower()):
                    has_button = True
                    break

        # Display and store elements that are either select fields or have related buttons
        if is_select or has_button:
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
