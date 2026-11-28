import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

import { adminKey, filesContaining } from './adminKey.js';

const dir = () => mkdtempSync(join(tmpdir(), 'admin-key-'));

test('the key comes from REGISTRY_ADMIN_KEY first, then the BuildKit secret file', () => {
  const secretFile = join(dir(), 'secret');
  writeFileSync(secretFile, 'from-file\n');
  assert.equal(adminKey({ env: { REGISTRY_ADMIN_KEY: ' from-env ' }, secretFile }), 'from-env');
  assert.equal(adminKey({ env: {}, secretFile }), 'from-file');
  assert.equal(adminKey({ env: {}, secretFile: join(dir(), 'missing') }), undefined);
});

test('an empty secret file means no key', () => {
  const secretFile = join(dir(), 'secret');
  writeFileSync(secretFile, '\n');
  assert.equal(adminKey({ env: {}, secretFile }), undefined);
});

test('the build scan finds the key in any nested output file and ignores missing roots', () => {
  const root = dir();
  mkdirSync(join(root, 'assets'));
  writeFileSync(join(root, 'index.html'), '<html>clean</html>');
  writeFileSync(join(root, 'assets', 'app.js'), 'const k="leaked-key-123";');
  assert.deepEqual(filesContaining('leaked-key-123', [root, join(root, 'nope')]), [join(root, 'assets', 'app.js')]);
  assert.deepEqual(filesContaining('other-key', [root]), []);
});
