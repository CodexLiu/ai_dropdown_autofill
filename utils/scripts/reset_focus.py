import time


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
