from test_case import initialize_browser
import time
from utils.scripts.verify_field_content import verify_field_content
from utils.scripts.analyze_form_fields import analyze_form_fields
from utils.scripts.visualize_element_changes import visualize_element_changes


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


def process_all_fields(page, clickable_elements):
    """Process all fields in sequence automatically"""
    print("\nProcessing all fields...")

    while True:  # Keep going until no more empty fields
        # Find first empty field
        empty_field_index = None
        for index, element in enumerate(clickable_elements):
            print(f"\nChecking field {index}: {element['label']}")

            # Skip if field already has content
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

        # Process the field using existing pipeline
        new_elements = visualize_element_changes(
            page, clickable_elements[empty_field_index], analyze_form_fields)

        # Update clickable elements and get fresh list
        if new_elements:
            clickable_elements = new_elements
        else:
            # If visualization failed, refresh the list anyway
            clickable_elements = analyze_form_fields(page)

        time.sleep(0.5)  # Small delay between fields

    return clickable_elements


def main():
    try:
        # Initialize browser and get pages
        chrome_process, playwright, browser, pages = initialize_browser()

        # Analyze forms on first page
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
                    continue
                elif choice.lower() == 'all':
                    print("\nProcessing all fields in sequence...")
                    clickable_elements = process_all_fields(
                        pages[0], clickable_elements)
                    continue

                element_index = int(choice)
                if 0 <= element_index < len(clickable_elements):
                    element = clickable_elements[element_index]
                    # Update clickable_elements with new analysis after visualization
                    new_elements = visualize_element_changes(
                        pages[0], element, analyze_form_fields)
                    if new_elements:
                        clickable_elements = new_elements
                else:
                    print("Invalid element number")
            except ValueError:
                if choice.lower() not in ['q', 'r', 'all']:
                    print(
                        "Please enter a valid number, 'all' to process all fields, 'r' to refresh, or 'q' to quit")

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
