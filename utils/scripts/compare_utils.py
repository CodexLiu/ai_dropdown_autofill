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
