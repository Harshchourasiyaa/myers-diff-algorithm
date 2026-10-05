import sys


# =============================================================================
# 1. MYERS DIFF (works on any indexable sequence of hashables)
# =============================================================================

def myers_diff(a, b):
    n, m = len(a), len(b)

    # Trivial cases: if one side is empty, the diff is just the other side.
    if n == 0:
        return [('+', -1, j) for j in range(m)]
    if m == 0:
        return [('-', i, -1) for i in range(n)]

    max_d = n + m
    offset = max_d
    size = 2 * max_d + 1

    v = [0] * size
    trace = []

    D = -1
    for d in range(max_d + 1):
        for k in range(-d, d + 1, 2):
            idx = offset + k
            if k == -d or (k != d and v[idx - 1] < v[idx + 1]):
                x = v[idx + 1]
            else:
                x = v[idx - 1] + 1
            y = x - k
            while x < n and y < m and a[x] == b[y]:
                x += 1
                y += 1
            v[idx] = x
            if x >= n and y >= m:
                D = d
                break
        trace.append(v.copy())
        if D != -1:
            break

    script = []
    x, y = n, m
    for d in range(D, 0, -1):
        vprev = trace[d - 1]
        k = x - y
        idx = offset + k
        if k == -d or (k != d and vprev[idx - 1] < vprev[idx + 1]):
            prev_k = k + 1
        else:
            prev_k = k - 1
        prev_x = vprev[offset + prev_k]
        prev_y = prev_x - prev_k

        while x > prev_x and y > prev_y:
            x -= 1
            y -= 1
            script.append(('=', x, y))

        if x == prev_x:
            script.append(('+', -1, y - 1))
            y -= 1
        else:
            script.append(('-', x - 1, -1))
            x -= 1

    while x > 0 and y > 0:
        x -= 1
        y -= 1
        script.append(('=', x, y))

    script.reverse()
    return script


# =============================================================================
# 2. DELETE-FIRST RULE
# =============================================================================

def deletes_before_inserts(script):
    result = []
    i, n = 0, len(script)

    while i < n:
        if script[i][0] == '=':
            result.append(script[i])
            i += 1
            continue

        j = i
        deletes, inserts = [], []
        while j < n and script[j][0] != '=':
            if script[j][0] == '-':
                deletes.append(script[j])
            else:
                inserts.append(script[j])
            j += 1

        result.extend(deletes)
        result.extend(inserts)
        i = j

    return result


# =============================================================================
# 3. FILE READING
# =============================================================================

def read_lines(path):
    with open(path, "rb") as f:
        data = f.read()
    if not data:
        return []
    lines = data.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    return lines


# =============================================================================
# 4. HIGHLIGHT HELPERS
# =============================================================================

def format_ranges(indices):
    """Coalesce sorted unique indices into 'start-end,start-end,...'."""
    ranges = []
    start = prev = indices[0]
    for i in indices[1:]:
        if i == prev + 1:
            prev = i
        else:
            ranges.append((start, prev + 1))
            start = prev = i
    ranges.append((start, prev + 1))
    return ",".join(f"{s}-{e}" for s, e in ranges)


def highlight_pair(old_line, new_line):
    """Return (old_ranges_str, new_ranges_str) for one paired -/+ line.

    old_line and new_line are raw bytes. Decode as UTF-8 so we work in
    Unicode code points, not bytes. The assignment says each emoji counts
    as one character, and '\\r' counts as one character too.
    """
    old_cp = list(old_line.decode("utf-8"))
    new_cp = list(new_line.decode("utf-8"))
    script = myers_diff(old_cp, new_cp)

    old_idx = sorted(i for k, i, _ in script if k == '-')
    new_idx = sorted(j for k, _, j in script if k == '+')
    return (format_ranges(old_idx) if old_idx else ".",
            format_ranges(new_idx) if new_idx else ".")


# =============================================================================
# 5. COMMANDS
# =============================================================================

def cmd_lines(path_a, path_b):
    a = read_lines(path_a)
    b = read_lines(path_b)
    script = deletes_before_inserts(myers_diff(a, b))

    out = sys.stdout.buffer
    for kind, i, j in script:
        if kind == '=':
            out.write(b' '); out.write(a[i]); out.write(b'\n')
        elif kind == '-':
            out.write(b'-'); out.write(a[i]); out.write(b'\n')
        else:
            out.write(b'+'); out.write(b[j]); out.write(b'\n')
    out.flush()


def cmd_highlight(path_a, path_b):
    a = read_lines(path_a)
    b = read_lines(path_b)
    script = deletes_before_inserts(myers_diff(a, b))

    out = sys.stdout.buffer
    i = 0
    n = len(script)

    while i < n:
        kind, ai, bj = script[i]

        if kind == '=':
            out.write(b' '); out.write(a[ai]); out.write(b'\n')
            i += 1
            continue

        # Collect the whole change block.
        deletes, inserts = [], []
        while i < n and script[i][0] != '=':
            k, ai, bj = script[i]
            if k == '-':
                deletes.append(a[ai])
            else:
                inserts.append(b[bj])
            i += 1

        # Print every '-' line first (delete-first rule).
        for line in deletes:
            out.write(b'-'); out.write(line); out.write(b'\n')

        # Now print each '+' line, followed immediately by its '?' line
        # if it is paired with a '-' line.
        for p, line in enumerate(inserts):
            out.write(b'+'); out.write(line); out.write(b'\n')
            if p < len(deletes):
                old_line = deletes[p]
                old_ranges, new_ranges = highlight_pair(old_line, line)
                out.write(b'? ')
                out.write(old_ranges.encode())
                out.write(b' | ')
                out.write(new_ranges.encode())
                out.write(b'\n')

    out.flush()


# =============================================================================
# 6. MAIN
# =============================================================================

def main(argv):
    if len(argv) < 4:
        print("usage: main.py <lines|highlight> A B", file=sys.stderr)
        return 2

    cmd, path_a, path_b = argv[1], argv[2], argv[3]

    if cmd not in ("lines", "highlight"):
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2

    try:
        with open(path_a, "rb"):
            pass
        with open(path_b, "rb"):
            pass
    except OSError as e:
        print(f"error: cannot read input: {e}", file=sys.stderr)
        return 2

    if cmd == "lines":
        cmd_lines(path_a, path_b)
    else:
        cmd_highlight(path_a, path_b)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))