// One-off helper: pushes the Handsel Gate source into the BrandGate
// repository as a new folder, handsgate/. Guarded by a token file that
// only exists on this machine, and only runs against a linked GitHub
// connection. Safe to delete after the push.
import { createFileRoute } from "@tanstack/react-router";
import { promises as fs } from "fs";
import path from "path";

const OWNER = "prekabreki";
const REPO = "BrandGate";
const BRANCH = "master";
const FOLDER = "handsgate";

const DIRECTORIES = [
  "src/brand",
  "src/components/handsel",
  "src/fixtures",
  "src/gate",
  "src/routes",
  "src/lib",
];

const SINGLE_FILES = [
  "src/router.tsx",
  "src/routeTree.gen.ts",
  "src/server.ts",
  "src/start.ts",
  "src/styles.css",
  "vite.config.ts",
  "tsconfig.json",
];

const README = `# Handsel Gate

The screen a brand team uses to review generated brand surfaces that the
scoring gate accepted or rejected. The tool is itself a Handsel surface:
it is set in the brand type, sits on the flow wash, and answers to the
same rules it reviews.

It is a static React review tool. There is no login and no backend. All
data comes from typed fixtures under \`src/fixtures/\`, shaped the way the
gate's own output is shaped, so the app can later read the same JSON from
disk.

## Run it

    cd handsgate
    bun install
    bun run dev

## Where things live

- \`src/fixtures/surfaces.ts\` — one entry per surface folder: the accepted
  candidate, the rejected candidate, and each candidate's full score.
- \`src/fixtures/rules.ts\` — the brand rules as editable prose, grouped
  under the section headings Mark, Colour, Gradient, Surface, Type,
  Motif, Motion.
- \`src/gate/rescore.ts\` — the seam. It is a lookup, not a scorer: the
  real gate is the Python pipeline in \`pipeline/\`, which reads the same
  rules file. When the two are wired together, this function is where
  the pipeline plugs in.
- \`src/brand/tokens.css\` — every colour, font, radius and shadow in the
  tool, defined once as CSS variables.

Editing a rule line in the right column calls \`rescore\` on blur and
updates the centre breakdown, so the rehearsed rule edits behave the way
they will once the real pipeline answers.
`;

async function collectFiles(root: string) {
  const files: { path: string; content: string }[] = [];

  for (const dir of DIRECTORIES) {
    const abs = path.join(root, dir);
    const entries = await fs.readdir(abs, { withFileTypes: true, recursive: true });
    for (const entry of entries) {
      if (!entry.isFile()) continue;
      const parent = entry.parentPath ?? entry.path ?? abs;
      const absFile = path.join(parent, entry.name);
      const rel = path.relative(root, absFile).split(path.sep).join("/");
      if (rel.endsWith(".md") && rel === "src/routes/README.md") continue;
      const content = await fs.readFile(absFile, "utf8");
      files.push({ path: `${FOLDER}/${rel}`, content });
    }
  }

  for (const rel of SINGLE_FILES) {
    const content = await fs.readFile(path.join(root, rel), "utf8");
    files.push({ path: `${FOLDER}/${rel}`, content });
  }

  const pkg = JSON.parse(await fs.readFile(path.join(root, "package.json"), "utf8"));
  pkg.name = "handsgate";
  delete pkg.lovable;
  files.push({ path: `${FOLDER}/package.json`, content: JSON.stringify(pkg, null, 2) + "\n" });

  files.push({ path: `${FOLDER}/README.md`, content: README });

  files.sort((a, b) => a.path.localeCompare(b.path));
  return files;
}

export const Route = createFileRoute("/api/public/handsgate-push")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const tokenFile = "/tmp/handsgate-push-token";
        let expected: string;
        try {
          expected = (await fs.readFile(tokenFile, "utf8")).trim();
        } catch {
          return new Response("This push route is not enabled.", { status: 404 });
        }
        if (!expected || request.headers.get("x-push-token") !== expected) {
          return new Response("Unauthorized", { status: 401 });
        }

        const lovableKey = process.env["LOVABLE_API_KEY"];
        const githubKey = process.env["GITHUB_API_KEY"];
        if (!lovableKey || !githubKey) {
          return new Response("The GitHub connection is not linked to this project.", { status: 500 });
        }

        const gateway = "https://connector-gateway.lovable.dev/github";
        const gh = async (p: string, init?: RequestInit) => {
          const res = await fetch(`${gateway}${p}`, {
            ...init,
            headers: {
              Accept: "application/vnd.github+json",
              "Content-Type": "application/json",
              Authorization: `Bearer ${lovableKey}`,
              "X-Connection-Api-Key": githubKey,
            },
          });
          if (!res.ok) throw new Error(`${p} failed: ${res.status} ${await res.text()}`);
          return res.json();
        };

        try {
          const candidates = [process.cwd(), "/dev-server"];
          let root = "";
          for (const c of candidates) {
            try {
              await fs.access(path.join(c, "src/routes/__root.tsx"));
              root = c;
              break;
            } catch {
              /* try next */
            }
          }
          if (!root) throw new Error("Could not locate the project source on disk.");

          const files = await collectFiles(root);

          const ref = await gh(`/repos/${OWNER}/${REPO}/git/ref/heads/${BRANCH}`);
          const headSha: string = ref.object.sha;
          const head = await gh(`/repos/${OWNER}/${REPO}/git/commits/${headSha}`);

          const tree = await gh(`/repos/${OWNER}/${REPO}/git/trees`, {
            method: "POST",
            body: JSON.stringify({
              base_tree: head.tree.sha,
              tree: files.map((f) => ({
                path: f.path,
                mode: "100644",
                type: "blob",
                content: f.content,
                encoding: "utf-8",
              })),
            }),
          });

          const commit = await gh(`/repos/${OWNER}/${REPO}/git/commits`, {
            method: "POST",
            body: JSON.stringify({
              message: "Add Handsel Gate, the review tool for gate verdicts",
              tree: tree.sha,
              parents: [headSha],
            }),
          });

          await gh(`/repos/${OWNER}/${REPO}/git/refs/heads/${BRANCH}`, {
            method: "PATCH",
            body: JSON.stringify({ sha: commit.sha, force: false }),
          });

          return Response.json({
            ok: true,
            files: files.length,
            commit: commit.sha,
            url: `https://github.com/${OWNER}/${REPO}/commit/${commit.sha}`,
          });
        } catch (err) {
          return new Response(
            JSON.stringify({ ok: false, error: String(err) }),
            { status: 500, headers: { "Content-Type": "application/json" } },
          );
        }
      },
    },
  },
});
