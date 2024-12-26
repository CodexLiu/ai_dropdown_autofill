from playwright.sync_api import sync_playwright
import time


def print_form_elements(page):
    """Print detailed information about all form and interactive elements"""
    print("\nInspecting form elements by traversing from buttons...")

    elements = page.evaluate('''() => {
        function getElementDetails(el) {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            
            // Get text content including child text
            const getText = (el) => {
                return el.textContent.trim() || el.value || el.placeholder || '';
            };

            // Find dropdown container by traversing up
            const findDropdownContainer = (el) => {
                let current = el;
                while (current && current !== document.body) {
                    // Check if current element is a dropdown container
                    if (current.className.includes('select') ||
                        current.className.includes('dropdown') ||
                        current.getAttribute('role') === 'combobox' ||
                        current.getAttribute('role') === 'listbox' ||
                        current.tagName === 'SELECT') {
                        return current;
                    }
                    current = current.parentElement;
                }
                return null;
            };

            // Get dropdown options
            const getDropdownOptions = (container) => {
                if (!container) return null;

                // Look for options in various forms
                const optionElements = container.querySelectorAll(
                    'option, [role="option"], .select-option, .dropdown-item, li'
                );

                if (optionElements.length) {
                    return Array.from(optionElements).map(opt => ({
                        text: opt.textContent.trim(),
                        value: opt.value || opt.getAttribute('data-value') || opt.textContent.trim(),
                        selected: opt.selected || opt.getAttribute('aria-selected') === 'true'
                    }));
                }

                return null;
            };

            // Get label by traversing up and looking for label elements
            const getLabel = (el) => {
                // First check for explicit label
                if (el.id) {
                    const explicitLabel = document.querySelector(`label[for="${el.id}"]`);
                    if (explicitLabel) {
                        return explicitLabel.textContent.trim();
                    }
                }

                // Look for label in ancestors
                let current = el;
                while (current && current !== document.body) {
                    // Check for label in siblings
                    const prevSibling = current.previousElementSibling;
                    if (prevSibling && 
                        (prevSibling.tagName === 'LABEL' || 
                         prevSibling.className.includes('label') ||
                         prevSibling.getAttribute('role') === 'label')) {
                        return prevSibling.textContent.trim();
                    }

                    // Check for label in parent's children
                    const parentLabel = current.parentElement?.querySelector('label, .label, [role="label"]');
                    if (parentLabel) {
                        return parentLabel.textContent.trim();
                    }

                    current = current.parentElement;
                }

                // Fallbacks
                return el.getAttribute('aria-label') || 
                       el.placeholder || 
                       el.name || 
                       '';
            };

            // Find the dropdown container if this is a button
            const dropdownContainer = findDropdownContainer(el);
            
            return {
                tag: el.tagName.toLowerCase(),
                text: getText(el),
                label: getLabel(dropdownContainer || el),
                id: el.id,
                name: el.name,
                type: el.type || '',
                value: el.value || '',
                class: el.className,
                role: el.getAttribute('role'),
                isVisible: el.offsetParent !== null,
                isEnabled: !el.disabled,
                isDropdown: !!dropdownContainer,
                dropdownContainer: dropdownContainer ? {
                    tag: dropdownContainer.tagName.toLowerCase(),
                    class: dropdownContainer.className,
                    role: dropdownContainer.getAttribute('role'),
                    options: getDropdownOptions(dropdownContainer)
                } : null,
                position: {
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height
                },
                attributes: Object.fromEntries(
                    Array.from(el.attributes)
                        .map(attr => [attr.name, attr.value])
                )
            };
        }

        // Start with buttons and clickable elements
        const selectors = [
            'button',
            '[role="button"]',
            '[class*="button"]',
            '[class*="btn"]',
            '[aria-haspopup="true"]',
            '[aria-expanded]',
            '.select-toggle',
            '.dropdown-toggle',
            'input[type="button"]',
            'input[type="submit"]'
        ];

        return Array.from(document.querySelectorAll(selectors.join(',')))
            .filter(el => {
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && 
                       style.visibility !== 'hidden' && 
                       style.opacity !== '0' &&
                       el.offsetParent !== null;
            })
            .map(getElementDetails);
    }''')

    # Group elements by type
    dropdowns = []
    buttons = []

    for el in elements:
        if el['isDropdown']:
            dropdowns.append(el)
        else:
            buttons.append(el)

    print("\n=== Dropdowns ===")
    for el in dropdowns:
        print_dropdown_details(el)

    print("\n=== Other Buttons ===")
    for el in buttons:
        print_button_details(el)


def print_dropdown_details(el):
    """Print detailed information about a dropdown"""
    print("\nDropdown:")
    print(f"Button Tag: {el['tag']}")
    print(f"Button Text: {el['text']}")
    print(f"Label: {el['label']}")
    if el['dropdownContainer']:
        print("\nContainer:")
        print(f"  Tag: {el['dropdownContainer']['tag']}")
        print(f"  Class: {el['dropdownContainer']['class']}")
        print(f"  Role: {el['dropdownContainer']['role']}")
        if el['dropdownContainer']['options']:
            print("\nOptions:")
            for opt in el['dropdownContainer']['options']:
                print(f"  - {opt['text']}", end='')
                if opt['selected']:
                    print(" (selected)", end='')
                print()
    print(f"\nPosition: {el['position']}")
    print(f"Classes: {el['class']}")
    print("Attributes:", el['attributes'])
    print("-" * 50)


def print_button_details(el):
    """Print detailed information about a button"""
    print("\nButton:")
    print(f"Tag: {el['tag']}")
    print(f"Text: {el['text']}")
    print(f"Label: {el['label']}")
    if el['id']:
        print(f"ID: {el['id']}")
    if el['name']:
        print(f"Name: {el['name']}")
    if el['type']:
        print(f"Type: {el['type']}")
    if el['role']:
        print(f"Role: {el['role']}")

    print(f"Is Enabled: {el['isEnabled']}")
    print(f"Position: {el['position']}")
    print(f"Classes: {el['class']}")
    print("Attributes:", el['attributes'])
    print("-" * 50)


def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            pages = context.pages

            if pages:
                print("\nAvailable pages:")
                for i, page in enumerate(pages):
                    print(f"{i}: {page.url}")

                page_choice = int(
                    input("\nWhich page would you like to analyze? (enter number): "))
                if 0 <= page_choice < len(pages):
                    current_page = pages[page_choice]
                    print(f"\nAnalyzing page: {current_page.url}")
                    print_form_elements(current_page)
                else:
                    print("Invalid page number")

                input("Press Enter to exit...")
            else:
                print("No pages found")
    except Exception as e:
        print("Error in main:", e)


if __name__ == "__main__":
    main()
