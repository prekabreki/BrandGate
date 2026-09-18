import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { type ReactNode } from "react";

import appCss from "../styles.css?url";
import glassCss from "../brand/glass.css?url";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-ground px-4">
      <div className="max-w-md text-center">
        <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-fg-soft">404</p>
        <h1 className="mt-3 font-display text-4xl font-extrabold tracking-[-0.035em] text-fg">
          Nothing is at this address.
        </h1>
        <p className="mt-3 text-fg-soft">
          The gate only has one page, and this is not it.
        </p>
        <div className="mt-7">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-chip bg-indigo px-4 py-2 font-mono text-[11px] uppercase tracking-[0.1em] text-paper transition-transform active:scale-[0.97]"
          >
            Back to the surfaces
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center bg-ground px-4">
      <div className="max-w-md text-center">
        <h1 className="font-display text-2xl font-extrabold tracking-[-0.03em] text-fg">
          This page did not load.
        </h1>
        <p className="mt-3 text-fg-soft">
          Something broke on the way in. Try again, or go back to the surfaces.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-chip bg-indigo px-4 py-2 font-mono text-[11px] uppercase tracking-[0.1em] text-paper transition-transform active:scale-[0.97]"
          >
            Try again
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-chip border border-hairline px-4 py-2 font-mono text-[11px] uppercase tracking-[0.1em] text-fg-soft transition-colors hover:text-fg"
          >
            Back to the surfaces
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      // The index route sets the real title and description; these are the
      // fallbacks a child route without a head would otherwise inherit.
      { title: "Handsel Gate" },
      { name: "description", content: "Review the surfaces the gate accepted and rejected." },
      { property: "og:title", content: "Handsel Gate" },
      { property: "og:description", content: "Review the surfaces the gate accepted and rejected." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
      // Linked separately on purpose; see the comment at the top of glass.css.
      {
        rel: "stylesheet",
        href: glassCss,
      },
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Archivo:wght@400;800&family=IBM+Plex+Mono:wght@400&display=swap",
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();

  return (
    <QueryClientProvider client={queryClient}>
      {/* Required: nested routes render here. Removing <Outlet /> breaks all child routes. */}
      <Outlet />
    </QueryClientProvider>
  );
}
