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
            try {
                // Get any associated label with proper CSS escaping
                let labelText = '';
                if (element.id) {
                    try {
                        const escapedId = CSS.escape(element.id);
                        const label = document.querySelector(`label[for="${escapedId}"]`);
                        if (label) labelText = label.textContent.trim();
                    } catch (e) {
                        console.log("Error finding label by ID, trying alternatives");
                    }
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
            } catch (e) {
                // Return minimal valid object if anything fails
                console.log("Error in getElementDetails, returning minimal info");
                return {
                    tag: element.tagName ? element.tagName.toLowerCase() : 'unknown',
                    id: '',
                    classes: [],
                    attributes: [],
                    textContent: '',
                    value: '',
                    dimensions: element.getBoundingClientRect(),
                    computedStyle: getComputedStyleProperties(element),
                    isVisible: true,
                    isFormField: false,
                    hasMouseListeners: false,
                    hasKeyboardListeners: false,
                    ariaAttributes: {
                        role: '',
                        label: '',
                        description: '',
                        expanded: '',
                        controls: '',
                        selected: '',
                        hidden: '',
                        value: '',
                        checked: ''
                    }
                };
            }
        }

        // Get ALL visible elements in the document, including form fields regardless of visibility
        function getAllVisibleElements() {
            try {
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
                    .map(el => {
                        try {
                            return getElementDetails(el);
                        } catch (e) {
                            // Skip problematic elements
                            return null;
                        }
                    })
                    .filter(Boolean); // Remove any null entries
            } catch (e) {
                console.log("Error in getAllVisibleElements, returning empty array");
                return [];
            }
        }

        // Get parent chain (up to 3 levels)
        let parentChain = [];
        try {
            let parent = el.parentElement;
            let level = 0;
            while (parent && level < 3) {
                try {
                    parentChain.push(getElementDetails(parent));
                } catch (e) {
                    // Skip problematic parent
                }
                parent = parent.parentElement;
                level++;
            }
        } catch (e) {
            console.log("Error getting parent chain");
        }

        // Get siblings
        const siblings = [];
        try {
            siblings.push(...Array.from(el.parentElement?.children || [])
                .filter(child => child !== el)
                .map(child => {
                    try {
                        return getElementDetails(child);
                    } catch (e) {
                        return null;
                    }
                })
                .filter(Boolean));
        } catch (e) {
            console.log("Error getting siblings");
        }

        // Get ALL children recursively
        function getAllChildren(element) {
            const children = [];
            try {
                function traverse(el) {
                    Array.from(el.children).forEach(child => {
                        try {
                            children.push(getElementDetails(child));
                            traverse(child);
                        } catch (e) {
                            // Skip problematic child
                        }
                    });
                }
                traverse(element);
            } catch (e) {
                console.log("Error getting children");
            }
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
