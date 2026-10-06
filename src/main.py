import sys
from array import array

def myers_diff(a, b):
    n, m = len(a), len(b)

    if n == 0:
        return [('+', -1, j) for j in range(m)]
    if m == 0:
        return [('-', i, -1) for i in range(n)]

    max_d = n + m
    offset = max_d
    v = [0] * (2 * max_d + 1)
    trace = []

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
                break

        # Only store the diagonals that are possible at this d.
        trace.append(array('i', v[offset - d:offset + d + 1]))

        if x >= n and y >= m:
            end_d = d
            break

    script = []
    x, y = n, m

    for d in range(end_d, 0, -1):
        prev = trace[d - 1]
        k = x - y

        if k == -d or (
            k != d and
            prev[(k - 1) + (d - 1)] < prev[(k + 1) + (d - 1)]
        ):
            prev_k = k + 1
        else:
            prev_k = k - 1

        prev_x = prev[prev_k + (d - 1)]
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

def delete_first(script):
    result = []
    i = 0

    while i < len(script):
        if script[i][0] == '=':
            result.append(script[i])
            i += 1
            continue

        deletes = []
        inserts = []

        while i < len(script) and script[i][0] != '=':
            if script[i][0] == '-':
                deletes.append(script[i])
            else:
                inserts.append(script[i])
            i += 1

        result.extend(deletes)
        result.extend(inserts)

    return result


def read_lines(path):
    with open(path, "rb") as f:
        lines = f.read().split(b"\n")

    if lines[-1] == b"":
        lines.pop()

    return lines


def format_ranges(indices):
    if not indices:
        return "."

    ranges = []
    start = prev = indices[0]

    for i in indices[1:]:
        if i == prev + 1:
            prev = i
        else:
            ranges.append(f"{start}-{prev + 1}")
            start = prev = i

    ranges.append(f"{start}-{prev + 1}")
    return ",".join(ranges)


def highlight_pair(old_line, new_line):
    old = list(old_line.decode("utf-8"))
    new = list(new_line.decode("utf-8"))
    script = myers_diff(old, new)

    old_idx = [i for k, i, _ in script if k == '-']
    new_idx = [j for k, _, j in script if k == '+']

    return format_ranges(old_idx), format_ranges(new_idx)


def cmd_lines(a_path, b_path):
    a = read_lines(a_path)
    b = read_lines(b_path)
    script = delete_first(myers_diff(a, b))
    out = sys.stdout.buffer

    for kind, i, j in script:
        if kind == '=':
            out.write(b' ' + a[i] + b'\n')
        elif kind == '-':
            out.write(b'-' + a[i] + b'\n')
        else:
            out.write(b'+' + b[j] + b'\n')


def cmd_highlight(a_path, b_path):
    a = read_lines(a_path)
    b = read_lines(b_path)
    script = delete_first(myers_diff(a, b))
    out = sys.stdout.buffer
    i = 0

    while i < len(script):
        if script[i][0] == '=':
            out.write(b' ' + a[script[i][1]] + b'\n')
            i += 1
            continue

        deletes = []
        inserts = []

        while i < len(script) and script[i][0] != '=':
            kind, ai, bj = script[i]

            if kind == '-':
                deletes.append(a[ai])
            else:
                inserts.append(b[bj])

            i += 1

        for line in deletes:
            out.write(b'-' + line + b'\n')

        for j, line in enumerate(inserts):
            out.write(b'+' + line + b'\n')

            if j < len(deletes):
                old_range, new_range = highlight_pair(deletes[j], line)
                out.write(
                    b'? ' + old_range.encode() +
                    b' | ' + new_range.encode() + b'\n'
                )


def main():
    if len(sys.argv) != 4:
        print("usage: main.py <lines|highlight> A B", file=sys.stderr)
        return 2

    command, a_path, b_path = sys.argv[1:]

    if command not in ("lines", "highlight"):
        print(f"unknown command: {command}", file=sys.stderr)
        return 2

    try:
        with open(a_path, "rb"):
            pass
        with open(b_path, "rb"):
            pass
    except OSError as e:
        print(f"error: cannot read input: {e}", file=sys.stderr)
        return 2

    if command == "lines":
        cmd_lines(a_path, b_path)
    else:
        cmd_highlight(a_path, b_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())