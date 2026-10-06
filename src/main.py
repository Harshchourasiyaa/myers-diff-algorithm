import sys
from itertools import groupby

def myers_diff(a, b):
    n, m = len(a), len(b)
    if not n: return [('+', -1, j) for j in range(m)]
    if not m: return [('-', i, -1) for i in range(n)]

    v, trace = {1: 0}, []
    for d in range(n + m + 1):
        trace.append(v.copy())
        for k in range(-d, d + 1, 2):
            x = v[k + 1] if k == -d or (k != d and v[k - 1] < v[k + 1]) else v[k - 1] + 1
            y = x - k
            while x < n and y < m and a[x] == b[y]:
                x += 1; y += 1
            v[k] = x
            if x >= n and y >= m:
                break
        if x >= n and y >= m:
            break

    script, x, y = [], n, m
    for d in range(len(trace) - 1, 0, -1):
        prev = trace[d]
        k = x - y
        prev_k = k + 1 if k == -d or (k != d and prev[k - 1] < prev[k + 1]) else k - 1
        px = prev[prev_k]
        py = px - prev_k

        while x > px and y > py:
            x -= 1; y -= 1
            script.append(('=', x, y))
        if x == px:
            y -= 1
            script.append(('+', -1, y))
        else:
            x -= 1
            script.append(('-', x, -1))

    while x > 0 and y > 0:
        x -= 1; y -= 1
        script.append(('=', x, y))

    return script[::-1]

def delete_first(script):
    res = []
    for eq, g in groupby(script, lambda op: op[0] == '='):
        res.extend(g if eq else sorted(g, key=lambda op: op[0] != '-'))
    return res

def read_lines(path):
    lines = open(path, "rb").read().split(b"\n")
    return lines[:-1] if lines[-1:] == [b""] else lines

def format_ranges(indices):
    if not indices: return "."
    runs = []
    for x in indices:
        if runs and x == runs[-1][1]:
            runs[-1][1] += 1
        else:
            runs.append([x, x + 1])
    return ",".join(f"{s}-{e}" for s, e in runs)

def highlight_pair(old_line, new_line):
    script = myers_diff(old_line.decode(), new_line.decode())
    return (format_ranges([i for k, i, _ in script if k == '-']),
            format_ranges([j for k, _, j in script if k == '+']))

def cmd_lines(a_path, b_path):
    cmd_highlight(a_path, b_path, highlight=False)

def cmd_highlight(a_path, b_path, highlight=True):
    a, b = read_lines(a_path), read_lines(b_path)
    out = sys.stdout.buffer
    for eq, hunk in groupby(delete_first(myers_diff(a, b)), lambda op: op[0] == '='):
        if eq:
            for _, i, _ in hunk:
                out.write(b' ' + a[i] + b'\n')
        else:
            hunk = list(hunk)
            dels = [a[i] for k, i, _ in hunk if k == '-']
            ins = [b[j] for k, _, j in hunk if k == '+']
            for line in dels:
                out.write(b'-' + line + b'\n')
            for j, line in enumerate(ins):
                out.write(b'+' + line + b'\n')
                if highlight and j < len(dels):
                    r1, r2 = highlight_pair(dels[j], line)
                    out.write(f"? {r1} | {r2}\n".encode())

def main():
    if len(sys.argv) != 4:
        print("usage: main.py <lines|highlight> A B", file=sys.stderr)
        return 2
    cmd, a, b = sys.argv[1:]
    if cmd not in ("lines", "highlight"):
        print(f"unknown command: {cmd}", file=sys.stderr)
        return 2
    try:
        for p in (a, b): open(p, "rb").close()
    except OSError as e:
        print(f"error: cannot read input: {e}", file=sys.stderr)
        return 2
    (cmd_lines if cmd == "lines" else cmd_highlight)(a, b)
    return 0

if __name__ == "__main__":
    sys.exit(main())