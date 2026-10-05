import sys

def _diff(a, b, a_lo, a_hi, b_lo, b_hi, out):
    # Trim common prefix (cheap win, shrinks the problem).
    while a_lo < a_hi and b_lo < b_hi and a[a_lo] == b[b_lo]:
        out.append(('=', a_lo, b_lo))
        a_lo += 1
        b_lo += 1
    # Collect common suffix separately — it must be emitted last.
    suffix = []
    while a_lo < a_hi and b_lo < b_hi and a[a_hi - 1] == b[b_hi - 1]:
        a_hi -= 1
        b_hi -= 1
        suffix.append(('=', a_hi, b_hi))

    if a_lo == a_hi:
        for j in range(b_lo, b_hi):
            out.append(('+', -1, j))
    elif b_lo == b_hi:
        for i in range(a_lo, a_hi):
            out.append(('-', i, -1))
    else:
        # Finding the middle snake and recurse on both halves.
        x, y, u, v = _middle_snake(a, b, a_lo, a_hi, b_lo, b_hi)
        _diff(a, b, a_lo, x, b_lo, y, out)
        for k in range(u - x):
            out.append(('=', x + k, y + k))
        _diff(a, b, u, a_hi, v, b_hi, out)

    out.extend(reversed(suffix))


def _middle_snake(a, b, a_lo, a_hi, b_lo, b_hi):
    n = a_hi - a_lo
    m = b_hi - b_lo
    delta = n - m
    odd = (delta & 1) != 0
    max_d = (n + m + 1) // 2 + 1
    offset = max_d
    size = 2 * max_d + 2

    # vf[k] = furthest x on forward diagonal k (k = x - y)
    # vb[k] = furthest x on backward diagonal k, measured from the *end*
    #         (i.e. vb[k] = (n - x_back), where x_back is forward x on that
    #         diagonal counted from the end).
    vf = [-1] * size
    vb = [-1] * size
    vf[offset + 1] = 0
    vb[offset + 1] = 0

    for d in range(max_d + 1):
        # ---------- forward ----------
        for k in range(-d, d + 1, 2):
            idx = offset + k
            if k == -d or (k != d and vf[idx - 1] < vf[idx + 1]):
                x = vf[idx + 1]
            else:
                x = vf[idx - 1] + 1
            y = x - k
            x0, y0 = x, y
            while x < n and y < m and a[a_lo + x] == b[b_lo + y]:
                x += 1
                y += 1
            vf[idx] = x

            if odd and -(d - 1) <= delta - k <= (d - 1):
                if vb[offset + (delta - k)] != -1:
                    if x + vb[offset + (delta - k)] >= n:
                        return (a_lo + x0, b_lo + y0, a_lo + x, b_lo + y)

        # ---------- backward ----------
        for k in range(-d, d + 1, 2):
            idx = offset + k
            if k == -d or (k != d and vb[idx - 1] < vb[idx + 1]):
                x = vb[idx + 1]
            else:
                x = vb[idx - 1] + 1
            y = x - k
            x0, y0 = x, y
            while x < n and y < m and a[a_hi - 1 - x] == b[b_hi - 1 - y]:
                x += 1
                y += 1
            vb[idx] = x

            if not odd and -d <= delta - k <= d:
                if vf[offset + (delta - k)] != -1:
                    if vf[offset + (delta - k)] + x >= n:
                        # Convert backward coordinates to forward.
                        fx_end = vf[offset + (delta - k)]
                        fy_end = fx_end - (delta - k)
                        # The backward snake (x0, y0)..(x, y) in reversed
                        # coordinates corresponds to forward coordinates:
                        bx = n - x
                        by = m - y
                        bx0 = n - x0
                        by0 = m - y0
                        return (a_lo + bx, b_lo + by, a_lo + bx0, b_lo + by0)

    raise RuntimeError("middle snake not found")


def myers_diff(a, b):
    n, m = len(a), len(b)
    if n == 0:
        return [('+', -1, j) for j in range(m)]
    if m == 0:
        return [('-', i, -1) for i in range(n)]
    out = []
    _diff(a, b, 0, n, 0, m, out)
    return out


# 2. DELETE-FIRST RULE

def deletes_before_inserts(script):
    result = []
    i, n = 0, len(script)
    while i < n:
        if script[i][0] == '=':
            result.append(script[i])
            i += 1
            continue
        j = i
        dels, adds = [], []
        while j < n and script[j][0] != '=':
            (dels if script[j][0] == '-' else adds).append(script[j])
            j += 1
        result.extend(dels + adds)
        i = j
    return result



# 3. FILE READING

def read_lines(path):
    with open(path, "rb") as f:
        data = f.read()
    if not data:
        return []
    lines = data.split(b"\n")
    if lines[-1] == b"":
        lines.pop()
    return lines


# 4. HIGHLIGHT HELPERS

def format_ranges(indices):
    """Coalesce sorted indices into 'a-b,c-d,...' (end exclusive)."""
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
    old_cp = list(old_line.decode("utf-8"))
    new_cp = list(new_line.decode("utf-8"))
    script = myers_diff(old_cp, new_cp)
    old_idx = sorted(i for k, i, _ in script if k == '-')
    new_idx = sorted(j for k, _, j in script if k == '+')
    return (format_ranges(old_idx) if old_idx else ".",
            format_ranges(new_idx) if new_idx else ".")


# 5. COMMANDS

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
    i, n = 0, len(script)
    while i < n:
        kind, ai, bj = script[i]
        if kind == '=':
            out.write(b' '); out.write(a[ai]); out.write(b'\n')
            i += 1
            continue

        deletes, inserts = [], []
        while i < n and script[i][0] != '=':
            k, ai, bj = script[i]
            if k == '-':
                deletes.append(a[ai])
            else:
                inserts.append(b[bj])
            i += 1

        for line in deletes:
            out.write(b'-'); out.write(line); out.write(b'\n')
        for p, line in enumerate(inserts):
            out.write(b'+'); out.write(line); out.write(b'\n')
            if p < len(deletes):
                old_ranges, new_ranges = highlight_pair(deletes[p], line)
                out.write(b'? ')
                out.write(old_ranges.encode())
                out.write(b' | ')
                out.write(new_ranges.encode())
                out.write(b'\n')
    out.flush()


# 6. MAIN

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
    (cmd_lines if cmd == "lines" else cmd_highlight)(path_a, path_b)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))