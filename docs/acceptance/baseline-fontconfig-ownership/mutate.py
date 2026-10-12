import sys, pathlib
target = pathlib.Path("src/bookscan/owned_tree.py")
orig = pathlib.Path(sys.argv[1]).read_text()
name = sys.argv[2]
M = {
 "names-unchecked": ('        if current.keys() != self._entries.keys():\n            raise NativeError("Private tree names changed; retaining it.")\n', ''),
 "root-unchecked": ('        if not self._root.matches(current):\n            raise NativeError("Private tree root was replaced or changed; retaining it.")\n', '        return\n'),
 "file-stamp-ignored": ('        return self.stamp == other.stamp\n', '        return True\n'),
 "symlink-target-ignored": ('if self.kind != other.kind or self.target != other.target:', 'if self.kind != other.kind:'),
 "dir-identity-ignored": ('return self.stamp[:3] == other.stamp[:3]', 'return True'),
 "prefetch-verify-dropped": ('        self.verify()\n        try:\n            for name', '        try:\n            for name'),
}
old, new = M[name]
assert orig.count(old) == 1, name
target.write_text(orig.replace(old, new))
