# Electrobun LLM Quickstart

This document is a condensed reference for LLMs setting up and developing Electrobun desktop applications. Electrobun is a TypeScript desktop framework using Bun as the runtime, native system webviews (or bundled CEF/Chromium), and Zig/C++ native bindings.

## Key Concepts

- **Main process**: TypeScript running on the Bun runtime (`electrobun/bun` imports). Manages windows, system tray, menus, and application lifecycle.
- **Browser/view process**: TypeScript running in a webview (`electrobun/view` imports). Standard web code (HTML/CSS/JS) with RPC bridge to the main process.
- **`views://` scheme**: Custom URL protocol that maps to bundled static assets. Use anywhere a URL is accepted in webviews.
- **`electrobun.config.ts`**: Central build configuration file in the project root.

## Project Setup

### Prerequisites

- [Bun](https://bun.sh) installed globally

### Scaffold a New Project

```bash
bunx electrobun init
# Choose from: hello-world, photo-booth, interactive-playground, multitab-browser
```

Or from scratch:

```bash
mkdir my-app && cd my-app
bun init .
bun install electrobun
```

### Minimal Project Structure

```
my-app/
├── src/
│   ├── bun/
│   │   └── index.ts          # Main process entry point
│   ├── mainview/
│   │   ├── index.ts           # Browser-side TypeScript
│   │   └── index.html         # UI template
│   └── shared/
│       └── types.ts           # Shared RPC type definitions
├── package.json
└── electrobun.config.ts
```

### package.json Scripts

```json
{
  "scripts": {
    "start": "electrobun dev",
    "dev": "electrobun dev --watch",
    "build:canary": "electrobun build --env=canary",
    "build:stable": "electrobun build --env=stable"
  },
  "dependencies": {
    "electrobun": "^0.0.1"
  }
}
```

### Minimal electrobun.config.ts

```ts
import type { ElectrobunConfig } from "electrobun";

export default {
  app: {
    name: "My App",
    identifier: "com.example.myapp",
    version: "0.0.1",
  },
  build: {
    bun: {
      entrypoint: "src/bun/index.ts",
    },
    views: {
      mainview: {
        entrypoint: "src/mainview/index.ts",
      },
    },
    copy: {
      "src/mainview/index.html": "views/mainview/index.html",
    },
  },
} satisfies ElectrobunConfig;
```

### Minimal Main Process (src/bun/index.ts)

```ts
import { BrowserWindow, ApplicationMenu } from "electrobun/bun";

// Enable standard edit keyboard shortcuts (Cmd+C, Cmd+V, etc.)
ApplicationMenu.setApplicationMenu([
  { submenu: [{ label: "Quit", role: "quit" }] },
  {
    label: "Edit",
    submenu: [
      { role: "undo" }, { role: "redo" },
      { type: "separator" },
      { role: "cut" }, { role: "copy" }, { role: "paste" },
      { role: "selectAll" },
    ],
  },
]);

const win = new BrowserWindow({
  title: "My App",
  url: "views://mainview/index.html",
  frame: { width: 1200, height: 800, x: 100, y: 100 },
});
```

## Remote Chrome DevTools Access (CEF)

This is critical for LLM-driven development and debugging. When using the CEF renderer, Electrobun exposes Chrome DevTools Protocol via a remote debugging port.

### Enabling Remote DevTools

**Step 1: Bundle CEF and set it as the default renderer in `electrobun.config.ts`:**

```ts
export default {
  // ...
  build: {
    mac: {
      bundleCEF: true,
      defaultRenderer: "cef",
      chromiumFlags: {
        "remote-debugging-port": "9222",
      },
    },
    linux: {
      bundleCEF: true,
      defaultRenderer: "cef",
      chromiumFlags: {
        "remote-debugging-port": "9222",
      },
    },
    win: {
      bundleCEF: true,
      defaultRenderer: "cef",
      chromiumFlags: {
        "remote-debugging-port": "9222",
      },
    },
  },
} satisfies ElectrobunConfig;
```

**Step 2: Programmatically open DevTools from the main process:**

```ts
// Open DevTools for the window's default webview
win.webview.openDevTools();

// Or toggle
win.webview.toggleDevTools();

// Close when done
win.webview.closeDevTools();
```

**Step 3: Connect remotely via Chrome DevTools Protocol:**

Once `remote-debugging-port` is set, you can connect to `http://localhost:9222` using:
- Chrome browser at `chrome://inspect`
- Any CDP client library (e.g., Puppeteer, Playwright)
- Direct websocket connection to the CDP endpoint

This enables programmatic DOM inspection, JavaScript evaluation, network monitoring, and console access — essential for LLM-driven automated testing and debugging.

### DevTools Behavior Notes

- On macOS with CEF, `openDevTools()` opens a separate remote DevTools window per webview (including nested OOPIFs/webview tags).
- On native WebKit (macOS without CEF), use Safari's Web Inspector instead.
- The `chromiumFlags` config accepts any Chromium command-line switch. Keys omit the `--` prefix. Values can be `true` (switch-only), a string (flag with value), or `false` (skip a default flag Electrobun normally sets).

## Enabling WebGPU (Dawn)

Electrobun can bundle a native WebGPU implementation (Dawn) for GPU rendering and compute directly from the Bun process — no browser webview required.

### Configuration

```ts
// electrobun.config.ts
export default {
  // ...
  build: {
    mac: { bundleWGPU: true },
    linux: { bundleWGPU: true },
    win: { bundleWGPU: true },
  },
} satisfies ElectrobunConfig;
```

### GPU Window (Bun-side rendering)

```ts
import { GpuWindow, webgpu } from "electrobun/bun";

const win = new GpuWindow({
  title: "WebGPU",
  frame: { width: 800, height: 600, x: 200, y: 120 },
});

const ctx = webgpu.createContext(win);
const adapter = await webgpu.navigator.requestAdapter({ compatibleSurface: ctx });
const device = await adapter.requestDevice();

ctx.configure({
  device,
  format: webgpu.navigator.getPreferredCanvasFormat(),
  alphaMode: "premultiplied",
});
```

### GPU View Inside a Web UI

Use the `<electrobun-wgpu>` custom element to embed a native GPU surface inside a webview layout. See the WGPU Tag docs for details.

### Compute Workloads

WebGPU compute pipelines work from Bun. Use `mapAsync` + `getMappedRange` for GPU readback:

```ts
await readbackBuffer.mapAsync(GPUMapMode.READ);
const mapped = readbackBuffer.getMappedRange();
const out = new Uint8Array(mapped.slice(0));
readbackBuffer.unmap();
```

### Raw FFI Access to Dawn

```ts
import { WGPU } from "electrobun/bun";

if (!WGPU.native.available) throw new Error("WGPU not bundled");
const instance = WGPU.native.symbols.wgpuCreateInstance(0);
```

### Dawn Source Code Reference

The Dawn source code is available locally at `/home/dylan/code/dawn`. **Always consult it when working with WebGPU FFI** — the prebuilt binary's API (struct layouts, enum values, function signatures) may differ from the upstream WebGPU spec.

The prebuilt `electrobun-dawn` v0.2.3 binary was built from Dawn commit **`75beadd1f3ab1c541ae743ef943480f434983a4e`**. If the version changes, check `package/build.ts` (`WGPU_VERSION`) and the corresponding release at https://github.com/blackboardsh/electrobun-dawn to find the new commit.

```bash
cd /home/dylan/code/dawn
git fetch origin 75beadd1f3ab1c541ae743ef943480f434983a4e
# Check a struct layout
git show 75beadd1f3:src/dawn/dawn.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d['texel copy texture info'], indent=2))"
# Check enum values
git show 75beadd1f3:src/dawn/dawn.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(json.dumps(d['texture usage'], indent=2))"
```

**The `dawn.json` file is the source of truth for the Dawn C API.** It defines all struct layouts, enum values, and function signatures. The C header (`webgpu.h`) is generated from it.

Key things to verify against `dawn.json`:
- **Struct layouts**: Check `"extensible"` field — if absent, the struct has NO `nextInChain` pointer. Newer Dawn "info" structs (like `texel copy texture info`) lack `nextInChain`, while "descriptor" structs still have it.
- **Enum/bitmask values**: Dawn's values may differ from the WebGPU spec. For example, texture `COPY_SRC` is `1` in Dawn but `4` in the spec.
- **Function argument types**: Method definitions in `dawn.json` show the exact struct types each function expects (e.g., `texel copy buffer info` vs the old `image copy buffer`).

### Engine Integrations

Electrobun re-exports `three` (Three.js) and `@babylonjs/core` (Babylon.js) for convenience. Use `webgpu.install()` and a canvas shim to render via `WebGPURenderer` or `WebGPUEngine`. See the WebGPU docs for full examples.

## RPC Between Main and Browser Processes

RPC is the primary communication mechanism. It is fully typed via a shared type definition.

### 1. Define Shared Types (src/shared/types.ts)

```ts
import type { RPCSchema } from "electrobun/bun";

export type MyRPC = {
  bun: RPCSchema<{
    requests: {
      getData: { params: { id: string }; response: { name: string } };
    };
    messages: {
      log: { msg: string };
    };
  }>;
  webview: RPCSchema<{
    requests: {
      updateUI: { params: { html: string }; response: boolean };
    };
    messages: {
      notify: { text: string };
    };
  }>;
};
```

### 2. Main Process (src/bun/index.ts)

```ts
import { BrowserWindow, BrowserView } from "electrobun/bun";
import type { MyRPC } from "../shared/types";

const rpc = BrowserView.defineRPC<MyRPC>({
  maxRequestTime: 5000,
  handlers: {
    requests: {
      getData: ({ id }) => ({ name: `Item ${id}` }),
    },
    messages: {
      log: ({ msg }) => console.log("Browser says:", msg),
    },
  },
});

const win = new BrowserWindow({
  title: "My App",
  url: "views://mainview/index.html",
  rpc,
});

// Call browser-side function from bun:
const result = await win.webview.rpc.request.updateUI({ html: "<b>Hello</b>" });

// Fire-and-forget message to browser:
win.webview.rpc.send.notify({ text: "Update available" });
```

### 3. Browser Process (src/mainview/index.ts)

```ts
import { Electroview } from "electrobun/view";
import type { MyRPC } from "../shared/types";

const rpc = Electroview.defineRPC<MyRPC>({
  handlers: {
    requests: {
      updateUI: ({ html }) => {
        document.body.innerHTML = html;
        return true;
      },
    },
    messages: {
      notify: ({ text }) => alert(text),
    },
  },
});

const electroview = new Electroview({ rpc });

// Call bun-side function from browser:
const data = await electroview.rpc.request.getData({ id: "42" });
```

### Built-in: evaluateJavascriptWithResponse

Every RPC-enabled webview has a built-in method to execute arbitrary JS and get a result:

```ts
const title = await win.webview.rpc.request.evaluateJavascriptWithResponse({
  script: "document.title",
});
```

## BrowserWindow Key Options

```ts
new BrowserWindow({
  title: "Window Title",
  url: "views://mainview/index.html",   // or any https:// URL
  html: "<h1>Inline HTML</h1>",         // alternative to url
  frame: { width: 1200, height: 800, x: 100, y: 100 },
  titleBarStyle: "default" | "hidden" | "hiddenInset",
  transparent: true,                     // transparent background
  sandbox: true,                         // disable RPC for untrusted content
  renderer: "cef" | "native",           // override default renderer
  partition: "persist:mypartition",      // session isolation
  preload: "console.log('preloaded')",   // inline JS or URL
  rpc: myRpcInstance,                    // typed RPC bridge
});
```

## Webview Tag (Nested OOPIFs)

Embed isolated webviews inside your HTML — each runs in a separate process:

```html
<electrobun-webview
  src="https://example.com"
  sandbox
  partition="third-party"
  style="width: 100%; height: 500px;"
></electrobun-webview>
```

Key attributes: `src`, `html`, `preload`, `partition`, `sandbox`, `transparent`, `renderer`.
Key methods: `loadURL()`, `goBack()`, `goForward()`, `reload()`, `setNavigationRules()`, `executeJavascript()`.

## CLI Commands

| Command | Description |
|---|---|
| `electrobun init [template]` | Scaffold a new project |
| `electrobun build [--env=dev\|canary\|stable]` | Build for current platform |
| `electrobun dev [--watch]` | Build + launch in dev mode |
| `electrobun run` | Launch an already-built dev bundle |

## Build Environments

| Environment | Code Signing | Artifacts | Use Case |
|---|---|---|---|
| `dev` | No | No | Local development |
| `canary` | Optional | Yes | Pre-release/beta testing |
| `stable` | Yes (if configured) | Yes | Production distribution |

## Platform Support

| Platform | System Webview | CEF (Bundled) | WebGPU (Dawn) |
|---|---|---|---|
| macOS (ARM64/x64) | WebKit (WKWebView) | Optional | Optional |
| Windows (x64) | WebView2 (Edge) | Optional | Optional |
| Linux (x64/ARM64) | WebKitGTK | Recommended | Optional |

**Linux note**: Bundling CEF is strongly recommended on Linux. The GTKWebKit renderer does not support advanced layer compositing features like `<electrobun-webview>` tags.

---

## Detailed Documentation Index

### Getting Started
- `docs/guides/quick-start.md` — Scaffold and run your first app
- `docs/guides/what-is-electrobun.md` — Architecture overview, performance comparisons
- `docs/guides/hello-world.md` — Step-by-step from-scratch tutorial
- `docs/guides/creating-ui.md` — Building UIs with webview tags, HTML, and menus

### Architecture & Internals
- `docs/guides/architecture/overview.md` — App structure, IPC, self-extracting bundles, code signing
- `docs/guides/architecture/webview-tag.md` — How the webview tag works internally

### Build & Distribution
- `docs/apis/cli/build-configuration.md` — Full `electrobun.config.ts` reference (ASAR, renderers, lifecycle hooks, chromium flags, watch config, URL schemes)
- `docs/apis/cli/cli-args.md` — CLI commands and build environments
- `docs/guides/bundling-and-distribution.md` — Packaging for release
- `docs/apis/bundled-assets.md` — The `views://` URL scheme for static assets
- `docs/apis/bundling-cef.md` — CEF configuration, mixed renderer support, custom CEF versions
- `docs/apis/application-icons.md` — App icon configuration

### Window & View APIs
- `docs/apis/browser-window.md` — BrowserWindow constructor, methods, events (close/resize/move/focus)
- `docs/apis/browser-view.md` — BrowserView API, DevTools, navigation, RPC, events

### Browser-Side APIs
- `docs/apis/browser/electroview-class.md` — Electroview class for browser-side RPC
- `docs/apis/browser/electrobun-webview-tag.md` — `<electrobun-webview>` element: attributes, methods, events, security
- `docs/apis/browser/draggable-regions.md` — Custom title bar drag regions
- `docs/apis/browser/global-properties.md` — Global browser properties
- `docs/apis/browser/wgpu-tag.md` — `<electrobun-wgpu>` element for embedding GPU surfaces

### GPU & WebGPU
- `docs/apis/webgpu.md` — Dawn bundling, GpuWindow, compute, FFI, Three.js/Babylon.js integration

### System APIs
- `docs/apis/bun.md` — Main process API overview and imports
- `docs/apis/context-menu.md` — Native context menus
- `docs/apis/application-menu.md` — Application menu bar
- `docs/apis/tray.md` — System tray icon and menu
- `docs/apis/paths.md` — Resource and view folder paths
- `docs/apis/utils.md` — Clipboard, file dialogs, notifications, quit, global shortcuts, screen info, sessions/cookies
- `docs/apis/events.md` — Event system, propagation, shutdown lifecycle
- `docs/apis/updater.md` — Built-in differential update system

### Cross-Platform & Compatibility
- `docs/guides/cross-platform-development.md` — Platform differences, CI builds, Linux recommendations
- `docs/guides/compatability.md` — Supported platforms, dependency versions
- `docs/guides/code-signing.md` — macOS code signing and notarization
- `docs/guides/updates.md` — Update system guide
