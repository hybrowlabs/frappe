'use strict';
/*
 * No-site harness for frappe/public/js/frappe/assets.js (the fork's asset-bundle resolution).
 *
 * Reads a JavaScript snippet on stdin, runs it as the body of an async function `(h) => {...}` and prints
 * JSON.stringify of what it returns. The real, unchanged assets.js is evaluated inside a `vm` context whose
 * `frappe`, `window`, `document` and `localStorage` are small recording stand-ins. No browser, no Frappe
 * server, no network. Synthetic values only (`example.invalid`).
 *
 * What the stand-ins do NOT do (each case lists it under Known gaps):
 *  - `document.createElement` returns a plain object; a "script" or "link" fires `onload` on the next tick
 *    and nothing is fetched or parsed.
 *  - `frappe.call` is a stub the snippet configures; the real server method is not reached.
 *  - `frappe.dom.freeze` and `unfreeze` only count their calls.
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..', '..');
const ASSETS_JS = path.join(ROOT, 'frappe', 'public', 'js', 'frappe', 'assets.js');

function build(options) {
  const opts = options || {};
  const calls = [];        // frappe.call arguments, in order
  const loaded = [];       // {tag, url} appended to document.head, in order
  const counters = { freeze: 0, unfreeze: 0 };

  const frappe = {
    boot: opts.noBoot ? undefined : { assets_json: opts.assetsJson, developer_mode: !!opts.developerMode },
    dom: {
      freeze() { counters.freeze += 1; },
      unfreeze() { counters.unfreeze += 1; },
    },
  };
  if (!opts.noCall) {
    frappe.call = (method) => {
      calls.push(method);
      if (opts.callImpl) return opts.callImpl(method);
      return Promise.resolve({ message: opts.callResponse });
    };
  }

  const document = {
    head: {
      appendChild(el) {
        loaded.push({ tag: el.tagName, url: el.src || el.href });
        setImmediate(() => el.onload && el.onload());
      },
    },
    createElement(tag) { return { tagName: tag }; },
  };

  const sandbox = {
    frappe,
    document,
    window: {
      location: { origin: 'https://site.example.invalid', hostname: 'site.example.invalid' },
      _version_number: 'v-test',
      performance: { getEntriesByType: () => [] },
    },
    localStorage: {},
    URL,
    Date,
    Promise,
    console: { log() {} },
    setTimeout,
  };
  sandbox.window.document = document;
  vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(ASSETS_JS, 'utf8'), sandbox, { filename: 'assets.js' });
  return { frappe, calls, loaded, counters, window: sandbox.window };
}

async function main() {
  const chunks = [];
  for await (const c of process.stdin) chunks.push(c);
  const body = Buffer.concat(chunks).toString('utf8');
  const fn = new Function('h', `return (async () => {${body}})();`);
  const result = await fn({ build });
  process.stdout.write(JSON.stringify(result === undefined ? null : result));
}

main().catch((e) => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
