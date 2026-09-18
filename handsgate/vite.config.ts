// @lovable.dev/vite-tanstack-config already includes the following — do NOT add them manually
// or the app will break with duplicate plugins:
//   - TanStack devtools (dev-only, first), tanstackStart, viteReact, tailwindcss, tsConfigPaths,
//     nitro (build-only using cloudflare as a default target), VITE_* env injection, @ path alias,
//     React/TanStack dedupe, error logger plugins, and sandbox detection (port/host/strictPort).
// You can pass additional config via defineConfig({ vite: { ... }, etc... }) if needed.
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

// Lightning CSS encodes a browser version as major << 16 | minor << 8 | patch.
const v = (major: number, minor = 0) => (major << 16) | (minor << 8);

export default defineConfig({
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
    // nitro/vite builds from this
    server: { entry: "server" },
  },
  vite: {
    css: {
      // Without explicit targets, Lightning CSS rewrote the glass recipe to
      // `-webkit-backdrop-filter` ONLY and deleted the standard property. Chrome does
      // not read the prefixed form, so every panel rendered as a flat fill, in dev and
      // in the build, with no error anywhere. A browserslist in package.json does not
      // reach it; these targets do. Each is the first version with backdrop-filter.
      lightningcss: {
        targets: {
          chrome: v(76),
          edge: v(79),
          firefox: v(103),
          safari: v(15, 4),
        },
      },
    },
  },
});
