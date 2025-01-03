def compare_states(before, after):
    changes = []
    for key in before:
        if key in ['computedStyle', 'ariaAttributes', 'dimensions']:
            continue
        if before[key] != after[key]:
            changes.append(f"  {key}: {before[key]} -> {after[key]}")

    if changes:
        print("\nGeneral Changes:")
        for change in changes:
            print(change)


def compare_styles(before, after):
    changes = []
    for key in before:
        if before[key] != after[key]:
            changes.append(f"  {key}: {before[key]} -> {after[key]}")

    if changes:
        for change in changes:
            print(change)


def compare_aria(before, after):
    changes = []
    for key in before:
        if before[key] != after[key]:
            changes.append(f"  {key}: {before[key]} -> {after[key]}")

    if changes:
        for change in changes:
            print(change)
