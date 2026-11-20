"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Blocks,
  LayoutDashboard,
  FolderKanban,
  Library,
  BookOpen,
  Activity,
  FileText,
  ArrowUpRight,
} from "lucide-react";

export const navigation = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/projects/", label: "Projects", icon: FolderKanban },
  { href: "/catalogue/", label: "Technology catalogue", icon: Library },
  { href: "/guides/", label: "Engineering guides", icon: BookOpen },
  { href: "/observability/", label: "Observability demo", icon: Activity },
  { href: "/docs/", label: "Documentation", icon: FileText },
];
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="workspace">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="BuildWise home">
          <span className="brand-icon">
            <Blocks size={22} />
          </span>
          BuildWise<span className="beta">BETA</span>
        </Link>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={
                pathname.replace(/\/$/, "") === href.replace(/\/$/, "")
                  ? "page"
                  : undefined
              }
            >
              <Icon size={19} aria-hidden="true" />
              {label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="tiny-label">BUILT WITH INTENTION</span>
          <p>
            Good engineering starts
            <br />
            with a clear plan.
          </p>
          <span className="text-xs text-slate-500">
            Deterministic. Explainable. Yours.
          </span>
        </div>
        <div className="sidebar-footer">
          <span className="avatar">BW</span>
          <div>
            Demo workspace
            <div className="text-xs text-slate-500">Free-tier foundation</div>
          </div>
          <ArrowUpRight size={16} className="ml-auto" aria-hidden="true" />
        </div>
      </aside>
      <div className="content-area">
        <header className="topbar">
          <span>
            Workspace <span className="mx-3 text-slate-300">/</span>{" "}
            <strong>
              {navigation.find(
                (item) =>
                  pathname.replace(/\/$/, "") === item.href.replace(/\/$/, ""),
              )?.label || "Workspace"}
            </strong>
          </span>
          <span className="topbar-tag">
            <span className="dot" />
            No paid AI. Just good engineering.
          </span>
        </header>
        <main id="main" tabIndex={-1}>
          {children}
        </main>
        <footer className="page-footer">
          BuildWise <span>From a good idea to a well-built system.</span>
          <span className="ml-auto">Public demo</span>
        </footer>
      </div>
    </div>
  );
}
