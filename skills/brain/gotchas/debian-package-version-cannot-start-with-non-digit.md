# Gotcha: Debian Package Version Cannot Start With a Non-Digit

## Symptom

When building a `.deb` in CI, `dpkg-deb --build` fails with:

```
dpkg-deb: error: parsing file '<pkg>/DEBIAN/control' near line 2 package '<name>':
 'Version' field value 'v2.4.2': version number does not start with digit
```

## Cause

Git release tags conventionally use a `v` prefix (`v1.0.0`, `v2.4.2`), but Debian policy requires the `Version:` field in `DEBIAN/control` to **start with a digit**. When a workflow extracts a tag from `GITHUB_REF` and pipes it straight into the control file, the leading `v` carries over and breaks the build the first time someone cuts a real release.

Broken pattern:

```bash
TAG="${GITHUB_REF#refs/tags/release/}"   # -> "v2.4.2"
cat > "${DEB_DIR}/DEBIAN/control" <<EOF
Package: my-app
Version: ${TAG}                          # -> "Version: v2.4.2"  ❌
...
EOF
```

## Fix

Strip the leading `v` before using the tag as a Debian version:

```bash
TAG="${GITHUB_REF#refs/tags/release/}"
VERSION="${TAG#v}"                       # -> "2.4.2"
cat > "${DEB_DIR}/DEBIAN/control" <<EOF
Package: my-app
Version: ${VERSION}                      # -> "Version: 2.4.2"  ✅
...
EOF
```

`${TAG#v}` is a no-op when there's no leading `v`, so it's safe across tag styles.

## How to spot this when reviewing or generating a workflow

Flag any workflow where **all three** are true:

1. It builds a `.deb` (calls `dpkg-deb`, writes a `DEBIAN/control` file, or has a `Version:` line in a heredoc).
2. The version is sourced from `GITHUB_REF`, `github.ref_name`, `git describe`, or any tag-derived variable.
3. There is **no explicit stripping of a leading `v`** (e.g. `${TAG#v}`, `sed 's/^v//'`, or equivalent).

If all three hold, the workflow will pass on dry runs (no tag → empty/clean version) and fail the first time someone tags `vX.Y.Z`.

## Related traps

- **RPM `Version:` fields** have similar constraints: must start with a digit, and unlike Debian, cannot contain `-`. Same fix applies.
- **Cargo.toml drift**: when generating package metadata in CI, prefer reading the version from the manifest (`cargo pkgid`, `cargo metadata --format-version 1 | jq -r '.packages[0].version'`) rather than the tag. The manifest is the source of truth and is already in the right format: no `v` to strip.
- **Debian version policy reference**: <https://www.debian.org/doc/debian-policy/ch-controlfields.html#version>