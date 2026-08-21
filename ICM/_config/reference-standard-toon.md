---
context-hierarchy: Layer 3
context-hierarchy-role: Reference material
immutable: true
recommended-context-tokens: 2500
tags: [TOON, syntax]
---

# Standard - TOON syntax

Quick reference for mapping JSON to TOON format. For rigorous, normative syntax rules and edge
cases, see the [Specification](https://toonformat.dev/reference/spec.md).

## Objects

```json [JSON]
{
  "id": 1,
  "name": "Ada"
}
```

```yaml [TOON]
id: 1
name: Ada
```

## Nested objects

```json [JSON]
{
  "user": {
    "id": 1,
    "name": "Ada"
  }
}
```

```yaml [TOON]
user:
  id: 1
  name: Ada
```

## Primitive arrays

```json [JSON]
{
  "tags": ["foo", "bar", "baz"]
}
```

```yaml [TOON]
tags[3]: foo,bar,baz
```

## Tabular arrays

```json [JSON]
{
  "items": [
    { "id": 1, "qty": 5 },
    { "id": 2, "qty": 3 }
  ]
}
```

```yaml [TOON]
items[2]{id,qty}:
  1,5
  2,3
```

## Mixed and non-uniform arrays

```json [JSON]
{
  "items": [1, { "a": 1 }, "x"]
}
```

```yaml [TOON]
items[3]:
  - 1
  - a: 1
  - x
```

> [!NOTE]
> When a list-item object has a tabular array as its first field, the tabular header appears on the
> hyphen line. Rows are indented two levels deeper than the hyphen, and other fields are indented
> one level deeper. This is the canonical encoding for this pattern.

```yaml [Multi-field object]
items[1]:
  - users[2]{id,name}:
      1,Ada
      2,Bob
    status: active
```

```yaml [Single-field object]
items[1]:
  - users[2]{id,name}:
      1,Ada
      2,Bob
```

## Arrays of arrays

```json [JSON]
{
  "pairs": [[1, 2], [3, 4]]
}
```

```yaml [TOON]
pairs[2]:
  - [2]: 1,2
  - [2]: 3,4
```

## Root arrays

```json [JSON]
["x", "y", "z"]
```

```yaml [TOON]
[3]: x,y,z
```

## Empty containers

```json [Empty Object]
{}
```

```yaml [Empty Object]
(empty output)
```

```json [Empty Array]
{
  "items": []
}
```

```yaml [Empty Array]
items: []
```

## Quoting special cases

### Strings that look like literals

```json [JSON]
{
  "version": "123",
  "enabled": "true"
}
```

```yaml [TOON]
version: "123"
enabled: "true"
```

These strings must be quoted because they look like numbers/booleans.

### Strings containing delimiters

```json [JSON]
{
  "note": "hello, world"
}
```

```yaml [TOON]
note: "hello, world"
```

Strings must be quoted when they contain the active delimiter (inside an array scope) or the
document delimiter (object field values, comma by default).

### Strings with leading/trailing spaces

```json [JSON]
{
  "message": " padded "
}
```

```yaml [TOON]
message: " padded "
```

### Empty string

```json [JSON]
{
  "name": ""
}
```

```yaml [TOON]
name: ""
```

## Quoting rules summary

Strings **must** be quoted if they:

* Are empty (`""`)
* Have leading or trailing whitespace
* Equal `true`, `false`, or `null` (case-sensitive)
* Look like numbers (e.g., `"42"`, `"-3.14"`, `"1e-6"`, `"05"`, `"+1"`)
* Contain special characters: `:`, `"`, `\`, `[`, `]`, `{`, `}`, or any control character
(U+0000-U+001F, including newline/tab/CR)
* Contain the relevant delimiter - the active delimiter inside an array scope, or the document
delimiter (comma by default) for object field values
* Equal `"-"` or start with `"-"` followed by any character
* Equal `"#"` or start with `"#"` (the line would read as a comment)

Otherwise, strings can be unquoted. Unicode and emoji are safe:

```yaml
message: Hello 世界 👋
note: This has inner spaces
```

## Escape sequences

Six escape sequences are valid in quoted strings:

| Character | Escape |
|-----------|--------|
| Backslash (`\`) | `\\` |
| Double quote (`"`) | `\"` |
| Newline | `\n` |
| Carriage return | `\r` |
| Tab | `\t` |
| Any other U+0000-U+001F control character | `\uXXXX` |

Other escapes (e.g. `\x`, `\0`, `\b`) are invalid, and lone-surrogate `\uXXXX` values
(U+D800-U+DFFF) are rejected.

## Array headers

### Basic header

```text
key[N]:
```

* `N` = array length
* Default delimiter: comma

### Tabular header

```text
key[N]{field1,field2,field3}:
```

* `N` = array length
* `{fields}` = column names
* Default delimiter: comma

### Nested field groups

```text
key[N]{id,customer{name,country},total}:
```

* `customer{...}` = a column of uniform sub-objects folded into the header
* Rows stay flat: cells follow a depth-first walk of the field list

See [Format Overview::Nested Field Groups](https://toonformat.dev/guide/format-overview.html#nested-field-groups)
for details.

### Alternative delimiters

```yaml [Tab Delimiter]
items[2 ]{id  name}:
  1 Ada
  2 Bob
```

```yaml [Pipe Delimiter]
items[2|]{id|name}:
  1|Ada
  2|Bob
```

The delimiter symbol appears inside the brackets and braces.

## Keyed tabular objects

An object of uniform objects collapses into a keyed header with one entry row per entry:

```yaml
users[2:]{age,city}:
  alice: 30,Berlin
  bob: 25,Paris
```

See [Format Overview::Keyed Tabular Objects](https://toonformat.dev/guide/format-overview.html#keyed-tabular-objects)
for details.

## Comments

Lines whose first non-space character is `#` are stripped before decoding:

```yaml
# Full-line comments only; encoders never emit them
host: example.com
```

## Type conversions

| Input | Output |
|-------|--------|
| Finite number in `[1e-6, 1e21)` (or zero) | Canonical decimal |
| Finite number outside that range | Exponent form permitted |
| `NaN`, `Infinity`, `-Infinity` | `null` |
| `BigInt` (safe range) | Number |
| `BigInt` (out of range) | Quoted decimal string |
| `Date` | ISO string (quoted) |
| `Set` | Array of normalized values |
| `Map` | Object with `String(key)` keys |
| `undefined`, `function`, `symbol` | `null` |

> [!INFO]
> TOON itself doesn't specify how `Date` should be encoded - the spec leaves this to implementations.
> This library emits an ISO 8601 string in quotes; other implementations may choose differently.
